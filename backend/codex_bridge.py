"""Claude (Anthropic) WebSocket bridge embedded in the backend."""
import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from anthropic import AsyncAnthropic
from fastapi import WebSocket, WebSocketDisconnect

PROJECT_ROOT = Path(os.getenv("CODEX_PROJECT_ROOT", Path(__file__).resolve().parents[1]))
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20240620")
STREAM_CHUNK_SIZE = int(os.getenv("CLAUDE_STREAM_CHUNK_SIZE", "80"))
STREAM_DELAY_MS = int(os.getenv("CLAUDE_STREAM_DELAY_MS", "12"))

sessions: Dict[str, Dict[str, Any]] = {}


def _load_skill_summaries() -> str:
    skills_dir = PROJECT_ROOT / ".agents" / "skills"
    if not skills_dir.exists():
        return "No skills directory found."

    summaries = []
    for skill_dir in sorted(skills_dir.iterdir()):
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue
        content = skill_file.read_text().splitlines()
        name = skill_dir.name
        desc = ""
        read_lines: List[str] = []
        write_lines: List[str] = []

        in_read = False
        in_write = False
        for line in content:
            if line.startswith("name:"):
                name = line.split(":", 1)[1].strip() or name
            if line.startswith("description:"):
                desc = line.split(":", 1)[1].strip(" >")
            if line.strip() == "## Read Endpoints":
                in_read, in_write = True, False
                continue
            if line.strip() == "## Write Endpoints":
                in_read, in_write = False, True
                continue
            if line.startswith("## "):
                in_read = False
                in_write = False
            if in_read and line.strip().startswith("- "):
                read_lines.append(line.strip()[2:])
            if in_write and line.strip().startswith("- "):
                write_lines.append(line.strip()[2:])

        read_summary = ", ".join(read_lines) if read_lines else "(none)"
        write_summary = ", ".join(write_lines) if write_lines else "(none)"
        summaries.append(f"- {name}: Read: {read_summary}. Write: {write_summary}. {desc}".strip())

    return "\n".join(summaries) if summaries else "No skills available."


SKILL_SUMMARY = _load_skill_summaries()


def _build_system_prompt(org_id: Optional[str], confirmed_id: Optional[str]) -> str:
    org_line = f"Active org: {org_id}" if org_id else "Active org: (none)"
    confirmed_line = (
        f"User has confirmed action id: {confirmed_id}. Proceed with ONLY that action."
        if confirmed_id
        else "No action has been confirmed yet."
    )

    instructions = [
        "You are a helpful AI assistant for PLG Lead Sourcer.",
        "You must only use the provided tool to call REST APIs. Never access the database directly.",
        "Available skills and endpoints:",
        SKILL_SUMMARY,
        "You have a valid API bearer token and optional org ID provided outside the model. Use the tool for all data access.",
        "For any write action (POST, PUT, DELETE), you MUST request confirmation first by responding with {\"type\":\"confirm\",...}.",
        "Do not call the tool for write actions until the user sends CONFIRM_ACTION: <id>.",
        confirmed_line,
        org_line,
        "",
        "Respond with raw JSON only (no markdown fences).",
        "Message: {\"type\":\"message\",\"text\":\"markdown allowed\"}",
        "Confirmation: {\"type\":\"confirm\",\"id\":\"action_id\",\"title\":\"...\",\"summary\":\"...\",\"method\":\"POST|PUT|DELETE\",\"path\":\"/api/...\",\"body\":{...}}",
    ]
    return "\n".join([line for line in instructions if line is not None])


TOOLS = [
    {
        "name": "plg_api_request",
        "description": "Call the PLG Lead Sourcer REST API. Use for read or write actions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "method": {"type": "string", "description": "HTTP method (GET, POST, PUT, DELETE)"},
                "path": {"type": "string", "description": "API path starting with /api/"},
                "params": {"type": "object", "description": "Query string parameters"},
                "body": {"type": "object", "description": "JSON body for POST/PUT requests"},
            },
            "required": ["method", "path"],
        },
    }
]


async def _execute_api_call(
    base_url: str,
    token: str,
    org_id: Optional[str],
    method: str,
    path: str,
    params: Optional[Dict[str, Any]],
    body: Optional[Dict[str, Any]],
) -> str:
    if not path.startswith("/api/"):
        return json.dumps({"error": "Path must start with /api/"})

    headers = {"Authorization": f"Bearer {token}"}
    if org_id:
        headers["X-Org-Id"] = org_id

    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        response = await client.request(
            method=method.upper(),
            url=path,
            params=params,
            json=body if method.upper() in {"POST", "PUT", "PATCH"} else None,
            headers=headers,
        )
        try:
            data = response.json()
        except ValueError:
            data = {"status_code": response.status_code, "text": response.text}
        return json.dumps(data)


async def _run_claude(
    websocket: WebSocket,
    message: str,
    token: str,
    org_id: Optional[str],
    api_base_url: str,
    session_id: str,
    confirmed_id: Optional[str],
):
    client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    if not os.getenv("ANTHROPIC_API_KEY"):
        await websocket.send_json({"type": "error", "message": "Missing ANTHROPIC_API_KEY"})
        return

    session = sessions.get(session_id) or {"messages": []}
    messages = session.get("messages", [])

    messages.append({"role": "user", "content": [{"type": "text", "text": message}]})

    await websocket.send_json({"type": "session.id", "sessionId": session_id})
    await websocket.send_json({"type": "turn.started"})

    system_prompt = _build_system_prompt(org_id, confirmed_id)

    while True:
        response = await client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
            tools=TOOLS,
        )

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                tool_input = block.input or {}
                method = (tool_input.get("method") or "GET").upper()
                path = tool_input.get("path") or ""
                params = tool_input.get("params") or None
                body = tool_input.get("body") or None

                await websocket.send_json({
                    "type": "agent.action",
                    "action": "tool_call",
                    "tool": f"{method} {path}",
                    "status": "started",
                })

                if method in {"POST", "PUT", "DELETE", "PATCH"} and not confirmed_id:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": "Write action blocked. Ask the user for confirmation.",
                        "is_error": True,
                    })
                    continue

                result = await _execute_api_call(
                    api_base_url, token, org_id, method, path, params, body
                )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
            continue

        # Final response
        text_parts = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text or "")
        final_text = "".join(text_parts).strip() or json.dumps({"type": "message", "text": "No response."})

        # Stream partial text updates for a smoother UX.
        if final_text:
            for idx in range(0, len(final_text), STREAM_CHUNK_SIZE):
                await websocket.send_json({
                    "type": "agent.text",
                    "text": final_text[: idx + STREAM_CHUNK_SIZE],
                    "status": "streaming",
                })
                if STREAM_DELAY_MS > 0:
                    await asyncio.sleep(STREAM_DELAY_MS / 1000)

        await websocket.send_json({
            "type": "agent.text",
            "text": final_text,
            "status": "done",
        })
        await websocket.send_json({
            "type": "turn.completed",
            "text": final_text,
            "usage": response.usage,
        })

        messages.append({"role": "assistant", "content": response.content})
        session["messages"] = messages
        sessions[session_id] = session
        break


async def codex_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            msg_type = msg.get("type")
            if msg_type == "reset":
                session_id = msg.get("sessionId")
                if session_id and session_id in sessions:
                    sessions.pop(session_id, None)
                await websocket.send_json({"type": "session.reset"})
                continue

            if msg_type != "chat":
                await websocket.send_json({"type": "error", "message": "Unknown message type"})
                continue

            message = (msg.get("message") or "").strip()
            if not message:
                await websocket.send_json({"type": "error", "message": "Message is required"})
                continue

            token = msg.get("token")
            if not token:
                await websocket.send_json({"type": "error", "message": "Missing bearer token"})
                continue

            session_id = msg.get("sessionId") or f"claude_{os.urandom(6).hex()}"
            confirmed_id = None
            if message.lower().startswith("confirm_action:"):
                confirmed_id = message.split(":", 1)[1].strip() or None

            api_base_url = msg.get("apiBaseUrl") or os.getenv("PLG_API_BASE_URL", "http://localhost:8000")

            await _run_claude(
                websocket,
                message,
                token,
                msg.get("orgId"),
                api_base_url,
                session_id,
                confirmed_id,
            )
    except WebSocketDisconnect:
        return
