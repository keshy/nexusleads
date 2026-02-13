# Chat Architecture — Codex SDK Agent with Generative UI

This document describes the chat feature for PLG Lead Sourcer (NexusLeads),
implemented as a **Codex SDK agent** that queries the database directly via
`psql` and returns structured responses rendered as generative UI.

---

## Overview

The chat is powered by the **OpenAI Codex CLI agent** — the same autonomous
coding agent you run from the terminal. We do **not** manage the conversation
loop, tool calling, or skill resolution ourselves. The Codex agent handles all
of that internally.

Our code is a thin **WebSocket relay** (`codex-bridge.js`) that:
1. Accepts a user message from the browser
2. Passes it to `thread.runStreamed()` (Codex SDK)
3. Forwards the agent's streaming events back to the browser

The Codex agent autonomously:
- Discovers `.agents/skills/*/SKILL.md` files from the working directory
- Decides which commands to run (`psql`, `cat`, `ls`, etc.)
- Executes them in a sandboxed environment
- Reasons over results across multiple steps
- Produces a final response

The frontend renders responses as **generative UI** — dashboard widgets,
tables, bar charts, and status pills — not just plain text.

```
┌──────────────────┐                  ┌──────────────────────────────────────────────────────┐
│                  │   WebSocket      │  Node.js Process (host, port 3001)                  │
│   Browser        │  ws://localhost  │                                                      │
│   ChatSidecar    │  :3001/ws/codex  │  ┌────────────────┐    ┌───────────────────────────┐ │
│   (React)        │◄────────────────►│  │ codex-bridge.js │    │  Codex CLI Agent          │ │
│                  │   JSON events    │  │ (WS relay only) │───►│  @openai/codex-sdk        │ │
└──────┬───────────┘                  │  │                 │◄───│                           │ │
       │                              │  │ • session mgmt  │    │  • Reads SKILL.md files   │ │
       │                              │  │ • event forward │    │  • Runs psql, cat, ls     │ │
       │                              │  │ • format hints  │    │  • Multi-step reasoning   │ │
       │                              │  └────────────────┘    │  • Manages conversation   │ │
       │                              │                         │  • Calls OpenAI API       │ │
       │                              │                         └─────────┬─────────────────┘ │
       │                              └───────────────────────────────────┼────────────────────┘
       │                                                                  │
       │ REST API                                    psql (sandboxed)     │  auto-discovered
       ▼                                                  │               ▼
┌──────────────────┐                   ┌──────────────────┴───┐  ┌─────────────────────┐
│ /api/chat/convos │                   │ PostgreSQL           │  │ .agents/skills/     │
│ (CRUD, FastAPI)  │                   │ localhost:5433       │  │ plg-database/       │
└──────┬───────────┘                   │ plg_lead_sourcer DB  │  │ SKILL.md            │
       │ reads/writes                  └──────────────────────┘  └─────────────────────┘
       ▼                                                         Agent reads these on its
┌──────────────────┐                                             own — we do NOT inject
│ Postgres         │                                             skill content into the
│ chat_conversations│                                            prompt.
└──────────────────┘
```

---

## Components

### 1. Codex Bridge (`assistant/codex-bridge.js`) — Thin WebSocket Relay

A Node.js WebSocket server that relays messages between the browser and the
**Codex CLI agent** (`@openai/codex-sdk`). Runs on the **host machine** (not
in Docker) for local development because the Codex CLI's Rust sandbox binary
has networking limitations inside Docker Desktop on macOS.

**What the bridge does (relay duties):**
- Accept WebSocket connections at `/ws/codex`
- Pass the user message + output format hints to `thread.runStreamed()`
- Forward Codex agent events (`agent.action`, `agent.text`, `turn.completed`) to the browser
- Manage Codex thread sessions (start/resume) for multi-turn conversations
- Send `turn.started` immediately on message receipt (latency optimization)
- Pre-warm the Codex SDK module on server start

**What the bridge does NOT do:**
- Parse or execute tool calls — the Codex agent does this autonomously
- Manage conversation history — Codex threads handle multi-turn state
- Inject skill content into the prompt — the agent discovers skills from the working directory
- Decide which commands to run — the agent reasons and acts on its own

**Sandbox configuration (passed to the Codex agent):**
- `sandboxMode: 'danger-full-access'` — allows `psql` to reach localhost
- `approvalPolicy: 'never'` — auto-approve all commands
- `skipGitRepoCheck: true`
- `workingDirectory` set to project root so skills are auto-discovered

**Start script:** `assistant/start-local.sh`

### 2. Database Skill (`.agents/skills/plg-database/SKILL.md`)

A single unified skill that teaches the Codex agent to query PostgreSQL
directly. Replaces the old per-resource API skills (archived in
`.agents/skills-archive/`).

The Codex agent **discovers this file automatically** by scanning
`.agents/skills/*/SKILL.md` in the working directory — the same mechanism
used when running `codex` from the terminal. Our bridge prompt contains only
a brief hint (`Use the $plg-database skill...`); the agent resolves the
skill reference and reads the file content on its own.

**What the skill file provides to the agent:**
- Full schema reference (projects, repositories, contributors, lead_scores, etc.)
- `psql` connection pattern via `DATABASE_URL` environment variable
- JSON output via `json_agg` for structured results
- Example queries for common operations
- Write confirmation protocol for INSERT/UPDATE/DELETE

**Query pattern (agent executes this autonomously):**
```bash
psql "$DATABASE_URL" -t -A -c "SELECT json_agg(t) FROM (...) t"
```

### 3. Chat Sidecar (`frontend/src/components/ChatSidecar.tsx`)

A slide-in panel that persists across all pages. Renders three response types
with rich, interactive UI.

**Features:**
- **Typewriter streaming** — latest bot message animates character by character
- **Expandable thinking steps** — live "Working..." indicator during processing,
  collapses to "Ran N steps ▶" when complete; each step is clickable to reveal
  the raw command
- **Generative UI dashboards** — structured data rendered as:
  - **Widget cards** — KPI metrics with gradient borders
  - **Bar charts** — horizontal bars with gradient fills
  - **Tables** — styled inline tables with headers
  - **Status pills** — colored badges for status breakdowns
- **Bouncing dots** — shown while waiting for first response
- **Markdown rendering** — for text-only responses
- **Confirmation UI** — for write operations
- **Conversation history** — CRUD via `/api/chat/conversations`
- **WebSocket reconnect** — with deduplication to prevent reconnect storms

### 4. Conversation Persistence (`backend/routers/chat.py`)

Conversations are stored in Postgres:
- Table: `chat_conversations`
- Stored per user and org
- CRUD endpoints: `/api/chat/conversations`

---

## Response Types

The bridge prompt includes **output format instructions** so the Codex agent
returns structured JSON that the frontend can render as generative UI. This is
the only "custom" part of our prompt — everything else (reasoning, tool
calling, skill usage, conversation state) is handled by the Codex agent.

The agent chooses the appropriate response format based on the query:

### 1. Text Message
For greetings, explanations, simple answers.
```json
{"type": "message", "text": "your **markdown** answer"}
```

### 2. Dashboard
For stats, summaries, counts, comparisons, overviews.
```json
{
  "type": "dashboard",
  "title": "Dashboard Title",
  "sections": [
    {"type": "widgets", "items": [{"title": "Label", "value": "42", "subtext": "info"}]},
    {"type": "bars", "label": "Chart Title", "items": [{"name": "X", "value": 10}]},
    {"type": "table", "columns": ["Name", "Status"], "rows": [{"Name": "x", "Status": "y"}]},
    {"type": "pills", "items": [{"label": "Active", "color": "green", "count": 5}]}
  ]
}
```

### 3. Confirm (Write Operations)
```json
{"type": "confirm", "id": "unique_id", "title": "Short title", "summary": "What will happen", "sql": "THE SQL"}
```

---

## WebSocket Protocol

**Browser → Assistant:**
- `chat`: `{ type: "chat", message, sessionId? }`
- `reset`: `{ type: "reset", sessionId }`

**Assistant → Browser:**
- `session.id`: `{ sessionId }`
- `turn.started`: signals processing has begun
- `agent.action`: `{ action: "command"|"tool_call", command|tool, status }`
- `agent.text`: `{ text, status: "streaming"|"done" }`
- `turn.completed`: `{ text, usage }`
- `error`: `{ message }`

---

## Environment

**Frontend (Docker)**
- `VITE_API_URL` → REST API base (`http://localhost:8000`)
- `VITE_CODEX_WS_URL` → WebSocket endpoint (`ws://localhost:3001/ws/codex`)

**Assistant (Host)**
- `DATABASE_URL` → Postgres connection (`postgresql://plg_user:plg_password@localhost:5433/plg_lead_sourcer`)
- `OPENAI_API_KEY` → via `~/.codex/auth.json` or environment
- `PROJECT_ROOT` → project root for skill discovery

No bearer tokens or API keys are sent from the browser. The assistant
authenticates with OpenAI via host credentials and queries the database
directly.

---

## Confirmation Flow (Writes)

1. User asks for a write (e.g., "create a project called Foo").
2. Agent queries the DB to validate, then responds with `{ type: "confirm", ... }`.
3. UI renders a Confirm/Cancel card.
4. Confirm sends `CONFIRM_ACTION: <id>`.
5. Agent executes the SQL write.

---

## Local Development

```bash
# Start infrastructure (Postgres, backend, frontend)
docker compose --profile dev up -d

# Start the assistant on the host
make assistant-local
```

The assistant runs on the host for local and production deployments. This keeps
the chat stack consistent and avoids Codex sandbox networking issues seen in
containerized assistant setups.

---

## Limitations & Notes

- The assistant requires a valid OpenAI API key (via `~/.codex/auth.json` or `OPENAI_API_KEY`).
- The Codex SDK's Rust sandbox binary does not work reliably inside Docker Desktop on macOS.
- Conversation history is stored per org; cross-org visibility is blocked by auth.
- The agent queries the database directly — no REST API intermediary for data access.
- `danger-full-access` sandbox mode is required for `psql` network access.
