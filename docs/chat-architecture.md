# Chat Architecture — Codex SDK Agent with Generative UI

This document describes the chat feature for PLG Lead Sourcer (NexusLeads),
implemented as a **Codex SDK agent** that queries the database directly via
`psql` and returns structured responses rendered as generative UI.

---

## Overview

The chat uses the **OpenAI Codex SDK** (`@openai/codex-sdk`) running on the
host machine. The agent reads skill files, executes `psql` commands inside a
sandboxed environment, and streams structured JSON responses to the browser
over WebSocket. The frontend renders these as rich dashboard widgets, tables,
bar charts, and status pills — not just plain text.

```
┌──────────────────┐   WebSocket       ┌─────────────────────┐   OpenAI API   ┌──────────────┐
│                  │  ws://localhost    │                     │  (streaming)   │              │
│   Browser        │  :3001/ws/codex   │  Node.js Assistant  │◄──────────────►│  OpenAI      │
│   ChatSidecar    │◄─────────────────►│  codex-bridge.js    │                │  GPT Model   │
│   (React)        │   JSON events     │  (host, port 3001)  │                │              │
└──────┬───────────┘                   └──────────┬──────────┘                └──────────────┘
       │                                          │
       │ REST API                                  │ psql (sandboxed)
       ▼                                          ▼
┌──────────────────┐                   ┌──────────────────────┐
│ /api/chat/convos │                   │ PostgreSQL           │
│ (CRUD, FastAPI)  │                   │ localhost:5433       │
└──────┬───────────┘                   │ plg_lead_sourcer DB  │
       │ reads/writes                  └──────────────────────┘
       ▼                                          ▲
┌──────────────────┐                              │ schema reference
│ Postgres         │                   ┌──────────┴──────────┐
│ chat_conversations│                  │ .agents/skills/     │
└──────────────────┘                   │ plg-database/       │
                                       │ SKILL.md            │
                                       └─────────────────────┘
```

---

## Components

### 1. Codex Bridge (`assistant/codex-bridge.js`)

A Node.js WebSocket server that wraps the `@openai/codex-sdk`. Runs on the
**host machine** (not in Docker) for local development because the Codex CLI's
Rust sandbox binary has networking limitations inside Docker Desktop on macOS.

**Responsibilities:**
- Accept WebSocket connections at `/ws/codex`
- Receive chat messages and stream agent events back
- Manage Codex thread sessions (start/resume)
- Pass `DATABASE_URL` to the sandbox environment
- Send `turn.started` immediately on message receipt (before async init)
- Pre-warm the Codex SDK module on server start

**Sandbox configuration:**
- `sandboxMode: 'danger-full-access'` — allows `psql` to reach localhost
- `approvalPolicy: 'never'` — auto-approve all commands
- `skipGitRepoCheck: true`
- `workingDirectory` set to project root so skills are discoverable

**Start script:** `assistant/start-local.sh`

### 2. Database Skill (`.agents/skills/plg-database/SKILL.md`)

A single unified skill that teaches the agent to query PostgreSQL directly.
Replaces the old per-resource API skills (archived in `.agents/skills-archive/`).

**Capabilities:**
- Full schema reference (projects, repositories, contributors, lead_scores, etc.)
- `psql` connection via `DATABASE_URL` environment variable
- JSON output via `json_agg` for structured results
- Example queries for common operations
- Write confirmation protocol for INSERT/UPDATE/DELETE

**Query pattern:**
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
docker compose up -d

# Start the assistant on the host
./assistant/start-local.sh
```

The assistant must run on the host for macOS local dev due to Codex CLI
sandbox limitations in Docker Desktop. On Linux (e.g., EC2), it can run
inside Docker.

---

## Limitations & Notes

- The assistant requires a valid OpenAI API key (via `~/.codex/auth.json` or `OPENAI_API_KEY`).
- The Codex SDK's Rust sandbox binary does not work reliably inside Docker Desktop on macOS.
- Conversation history is stored per org; cross-org visibility is blocked by auth.
- The agent queries the database directly — no REST API intermediary for data access.
- `danger-full-access` sandbox mode is required for `psql` network access.
