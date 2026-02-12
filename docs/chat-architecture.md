# Chat Architecture — Claude-Powered Agent

This document describes the chat feature for PLG Lead Sourcer, implemented as a
Claude-powered agent that uses API-only skills (no direct DB access).

---

## Overview

The chat is not a simple LLM prompt-response loop. It uses **Claude** with tool
calling to run API requests and reason over multiple steps. The backend hosts a
WebSocket endpoint that streams events to the frontend
sidecar UI.

```
┌──────────────┐   WebSocket    ┌──────────────────┐   Claude API   ┌──────────────┐
│              │  /ws/codex     │                  │  (tools)      │              │
│   Browser    │◄──────────────►│  FastAPI WS      │◄─────────────►│  Claude Model│
│  Sidecar UI  │   JSON msgs    │  codex_bridge.py │               │              │
└──────┬───────┘                └──────────────────┘               └──────┬───────┘
       │                                                                  │
       │ REST API                                                         │ uses skills
       ▼                                                                  ▼
┌──────────────────┐                                             ┌────────────────────┐
│ /api/chat/convos │                                             │ .agents/skills/*   │
│ (CRUD)           │                                             │ REST API skills    │
└──────┬───────────┘                                             └────────────────────┘
       │ reads/writes
       ▼
┌──────────────────┐
│ Postgres         │
│ chat_conversations│
└──────────────────┘
```

---

## Components

### 1. WebSocket Bridge (`backend/codex_bridge.py`)

A FastAPI WebSocket endpoint that calls Claude with tool usage and streams
agent events to the browser.

**Responsibilities:**
- Accept WebSocket connections from the chat sidecar
- Receive `{ type: "chat", message, token, orgId, apiBaseUrl, sessionId? }`
- Call Claude with tool usage and stream events
- Maintain in-memory message history for multi-turn sessions
- Enforce confirmation flow for write actions

**Key design decisions:**
- **API-only access.** The agent is taught to use API skills only.
- **Tool-calling.** Claude uses a single API request tool to call REST endpoints.
- **Network access.** The backend performs API calls with the user’s token.
- **Confirmation gate for writes.** The model must emit `type: "confirm"` and wait
  for `CONFIRM_ACTION: <id>`.

**Message protocol (browser → server):**
- `chat`: `{ message, token, orgId?, apiBaseUrl?, sessionId? }`
- `reset`: `{ sessionId }`

**Message protocol (server → browser):**
- `session.id`: `{ sessionId }`
- `turn.started`
- `agent.text`: `{ text, status }`
- `agent.action`: `{ action, command|tool, status }`
- `turn.completed`: `{ text, usage }`
- `error`: `{ message }`

### 2. Assistant Skills (`.agents/skills/*/SKILL.md`)

Each API resource has its own skill file. Skills define:
- Base URL and auth headers (`Authorization` + optional `X-Org-Id`)
- Read endpoints (GET)
- Write endpoints (POST/PUT/DELETE)
- Required confirmation format for writes

**Write confirmation format:**
```json
{"type":"confirm","id":"action_id","title":"...","summary":"...","method":"POST|PUT|DELETE","path":"/api/...","body":{...}}
```

The UI renders a confirm card; confirming sends `CONFIRM_ACTION: <id>`.

### 3. Chat Sidecar (`frontend/src/components/ChatSidecar.tsx`)

A slide-in panel that persists across all pages.

**Features:**
- WebSocket client with reconnect
- Multi-turn session tracking via `sessionId`
- Action indicators for agent commands
- Markdown rendering for answers
- Confirmation UI for write actions
- Conversation history (CRUD via `/api/chat/conversations`)

### 4. Conversation Persistence (`backend/routers/chat.py`)

Conversations are stored in Postgres:
- Table: `chat_conversations`
- Stored per user and org
- CRUD endpoints: `/api/chat/conversations`

---

## Environment and Auth

**Frontend**
- `VITE_API_URL` → REST API base
- `VITE_CODEX_WS_URL` → WebSocket endpoint (defaults to `/ws/codex`)

**Backend**
- `PLG_API_BASE_URL` → used by the assistant for API calls
- `CLAUDE_MODEL` → model name (default `claude-3-5-sonnet-20240620`)
- `ANTHROPIC_API_KEY` → required for Claude API access

**Bearer token** is sent from the browser on each message and used by the backend
to call the API with the user’s session context.

---

## Confirmation Flow (Writes)

1. User asks for a write (e.g., create a project).
2. Codex responds with `{ type: "confirm", ... }`.
3. UI shows Confirm/Cancel.
4. Confirm sends `CONFIRM_ACTION: <id>`.
5. Codex executes the write API call.

---

## Limitations & Notes

- The backend requires a valid `ANTHROPIC_API_KEY`.
- Large API responses can slow the agent; skills should keep calls scoped.
- Conversation history is stored per org; cross-org visibility is blocked by auth.
- The agent does not access the DB directly by design.
