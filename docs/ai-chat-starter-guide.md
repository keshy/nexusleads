---
name: add-ai-chat
description: >
  Scaffold an AI-native chat / assistant interface into any application.
  Uses the OpenAI Codex SDK as the autonomous agent. The agent discovers
  your data sources (database, REST API, filesystem, CLI tools — whatever
  your app uses) via a SKILL.md file and returns structured JSON that the
  frontend renders as generative UI (dashboard widgets, tables, bar charts,
  status pills) with streaming UX.
---

# Add AI Chat to Your Application

You are scaffolding an AI-native chat interface for the user's application.
Follow the steps below to generate all required files.

## What This Creates

- `assistant/` — Node.js WebSocket relay wrapping the Codex CLI agent (~100 LOC)
- `.agents/skills/<app-name>/SKILL.md` — teaches the agent about the app's data
- Frontend chat component with generative UI rendering
- Streaming UX: typewriter effect, live thinking steps, bouncing dots

The **Codex CLI agent handles all the hard parts** — reasoning, tool calling,
multi-step execution, conversation state. Your code is a thin WebSocket relay
that forwards events, plus a frontend that renders structured responses.

## Before You Start

Ask the user:
1. **What is your app called?** (used for naming)
2. **How does your app store/access data?** Pick all that apply:
   - PostgreSQL / MySQL / SQLite (direct SQL via `psql`, `mysql`, `sqlite3`)
   - REST API (via `curl`)
   - GraphQL API (via `curl`)
   - Filesystem / JSON files (via `cat`, `jq`, `node -e`)
   - Redis / MongoDB / other CLI tools
3. **What are the main entities / domain objects?** (e.g., users, orders, products)
4. **What frontend framework?** (React, Vue, vanilla JS, etc.)
5. **Are there any sensitive fields to hide?** (passwords, tokens, secrets)

Use the answers to fill in the templates below.

---

## Step 1 — Create the Data Skill

Create `.agents/skills/<app-name>/SKILL.md`.

The Codex agent discovers this file automatically from the working directory.
You do NOT inject its content into the prompt — the agent reads it on its own.

### Template

```markdown
---
name: <app-name>-data
description: >
  Use when the user asks about <list of domain entities>.
  Access the application's data using <data access method>.
---

# <App Name> Data Skill

You are a data assistant for <App Name>.

## Data Access

<< Pick the section(s) that match the user's data sources. >>

### Option A: SQL Database

Connection:
\```bash
CONN="${DATABASE_URL}"
\```

Query pattern:
\```bash
psql "$CONN" -t -A -c "SELECT json_agg(t) FROM (YOUR QUERY) t"
\```

### Option B: REST API

\```bash
curl -s -H "Authorization: Bearer $API_TOKEN" \
  ${API_BASE_URL}/api/endpoint | jq .
\```

### Option C: Filesystem / JSON

\```bash
cat data/entities.json | jq '.[] | select(.status == "active")'
\```

### Option D: Any CLI Tool

\```bash
<tool> <args>
\```

## Response Format

Always respond with raw JSON (no markdown fences around it).

### Text answer (greetings, explanations, simple questions)
\```json
{"type":"message","text":"your **markdown** answer"}
\```

### Dashboard answer (stats, summaries, counts, comparisons, overviews)
\```json
{"type":"dashboard","title":"Dashboard Title","sections":[...]}
\```

Section types:
- `{"type":"widgets","items":[{"title":"Label","value":"42","subtext":"extra info"}]}`
  KPI cards: counts, totals, key metrics (2–4 items)
- `{"type":"bars","label":"Chart Title","items":[{"name":"Label","value":10}]}`
  Ranked lists, distributions, comparisons
- `{"type":"table","columns":["Name","Status"],"rows":[{"Name":"x","Status":"y"}]}`
  Detailed listings with multiple columns
- `{"type":"pills","items":[{"label":"Active","color":"green","count":5}]}`
  Status breakdowns. Colors: green, red, yellow, blue, orange

Combine multiple sections in one dashboard.

### Confirm answer (write/mutate operations)
\```json
{"type":"confirm","id":"unique_id","title":"Short title","summary":"What will happen","action":"THE COMMAND OR SQL"}
\```

## Data Model

<< Document your entities here. For SQL, use schema tables.
   For APIs, list endpoints and response shapes.
   For files, describe the JSON structure. >>

### Example: SQL table
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| name | VARCHAR(255) | |
| status | VARCHAR(50) | active, inactive |
| created_at | TIMESTAMPTZ | |

### Example: REST endpoint
GET /api/orders — returns `[{"id": "...", "total": 99.50, "status": "shipped"}]`

### Example: JSON file
`data/products.json` — array of `{"sku": "...", "name": "...", "price": 10.00}`

## Example Queries

<< Provide 3–5 examples that cover common operations.
   The agent learns patterns and adapts them. >>

## Write Operations

For any write/mutate operation, you MUST ask for confirmation first.
Return a confirm payload and wait for the user to approve.

## Security

- Never expose: <list sensitive fields>
- Limit results to 20 rows by default
```

### Skill Design Principles

- **One skill file, full data model.** Don't split per-entity — the agent
  wastes turns figuring out which skill to use.
- **Include example queries.** 3–5 examples cover most use cases. The agent
  adapts the patterns.
- **Structured output.** Prefer JSON output from your data source so the
  agent can reason over it and format for the UI.
- **Response format in the skill.** The agent reads this and produces the
  right JSON structure for the frontend.
- **Security boundaries.** Explicitly list what NOT to expose.
- **Data-source agnostic.** The skill can use any CLI tool — `psql`, `curl`,
  `mysql`, `sqlite3`, `mongosh`, `redis-cli`, `cat | jq`, `node -e`,
  `python -c`, or any combination.

---

## Step 2 — Create the WebSocket Bridge

This is a thin relay. It does NOT manage the conversation loop, execute
tools, or inject skill content. The Codex agent does all of that.

### Create `assistant/package.json`

```json
{
  "name": "<app-name>-assistant",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "@openai/codex-sdk": "^0.98.0",
    "express": "^4.18.2",
    "ws": "^8.16.0"
  }
}
```

### Create `assistant/server.js`

```javascript
const express = require('express');
const http = require('http');
const { attachWebSocketServer, warmup } = require('./codex-bridge');

const PORT = process.env.PORT || 3001;
const app = express();
app.get('/health', (_req, res) => res.json({ status: 'ok' }));

const server = http.createServer(app);
attachWebSocketServer(server);

server.listen(PORT, () => {
  console.log(`Assistant listening on port ${PORT}`);
  warmup().then(() => console.log('[codex] SDK pre-warmed')).catch(() => {});
});
```

### Create `assistant/codex-bridge.js`

```javascript
const { WebSocketServer } = require('ws');
const path = require('path');

let CodexModule = null;
async function getCodex() {
  if (!CodexModule) CodexModule = await import('@openai/codex-sdk');
  return CodexModule;
}

const projectRoot = process.env.PROJECT_ROOT || path.resolve(__dirname, '..');
const sessions = new Map();

function safeSend(ws, data) {
  if (ws.readyState === 1) {
    ws.send(typeof data === 'string' ? data : JSON.stringify(data));
    return true;
  }
  return false;
}

function attachWebSocketServer(httpServer) {
  const wss = new WebSocketServer({ server: httpServer, path: '/ws/codex' });
  wss.on('connection', (ws) => {
    ws.on('message', async (raw) => {
      let msg;
      try { msg = JSON.parse(raw.toString()); } catch {
        ws.send(JSON.stringify({ type: 'error', message: 'Invalid JSON' }));
        return;
      }
      if (msg.type === 'chat') await handleChat(ws, msg);
      else if (msg.type === 'reset') {
        if (msg.sessionId) sessions.delete(msg.sessionId);
        ws.send(JSON.stringify({ type: 'session.reset' }));
      }
    });
  });
}

async function handleChat(ws, msg) {
  const { message, sessionId, confirmedActionId } = msg;
  if (!message?.trim()) {
    safeSend(ws, { type: 'error', message: 'Message is required.' });
    return;
  }

  // Send turn.started IMMEDIATELY — before any async work — for perceived speed
  let currentSessionId = sessionId || `codex_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  safeSend(ws, { type: 'session.id', sessionId: currentSessionId });
  safeSend(ws, { type: 'turn.started' });

  try {
    const { Codex } = await getCodex();

    // ── CUSTOMIZE: pass env vars your skill needs to the sandbox ──
    const codex = new Codex({
      env: {
        PATH: process.env.PATH,
        HOME: process.env.HOME || '/tmp',
        // Add whatever your skill needs:
        // DATABASE_URL: process.env.DATABASE_URL,
        // API_BASE_URL: process.env.API_BASE_URL,
        // API_TOKEN: process.env.API_TOKEN,
      },
    });

    const threadOptions = {
      workingDirectory: projectRoot,
      sandboxMode: 'danger-full-access',
      approvalPolicy: 'never',
      skipGitRepoCheck: true,
    };

    const session = sessionId ? sessions.get(sessionId) : null;
    let thread;
    if (session?.threadId) {
      thread = codex.resumeThread(session.threadId, threadOptions);
      currentSessionId = sessionId;
    } else {
      thread = codex.startThread(threadOptions);
    }

    // ── CUSTOMIZE: update the app name and skill reference ──
    const prompt = buildPrompt(message, confirmedActionId);
    const streamed = await thread.runStreamed(prompt);
    let finalText = '';

    for await (const event of streamed.events) {
      if (ws.readyState !== 1) break;

      if (event.type === 'thread.started') {
        sessions.set(currentSessionId, { threadId: event.thread_id });
      }

      if (event.type === 'item.started' || event.type === 'item.completed') {
        const item = event.item;
        if (!item) continue;
        if (item.type === 'agent_message') {
          const text = item.content || item.text || '';
          if (text) {
            finalText = text;
            safeSend(ws, { type: 'agent.text', text, status: event.type === 'item.completed' ? 'done' : 'streaming' });
          }
        } else if (item.type === 'command_execution' && event.type === 'item.started') {
          safeSend(ws, { type: 'agent.action', action: 'command', command: item.command || '', status: 'started' });
        }
      }

      if (event.type === 'turn.completed') {
        safeSend(ws, { type: 'turn.completed', text: finalText, usage: event.usage || null });
      }
      if (event.type === 'turn.failed') {
        safeSend(ws, { type: 'error', message: event.error?.message || 'Turn failed' });
      }
      if (event.type === 'error') {
        safeSend(ws, { type: 'error', message: event.message || 'Stream error' });
      }
    }
  } catch (err) {
    safeSend(ws, { type: 'error', message: err.message || 'Codex bridge error' });
  }
}

function buildPrompt(message, confirmedActionId) {
  const confirmedLine = confirmedActionId
    ? `User has confirmed action id: ${confirmedActionId}. Proceed.`
    : '';

  return [
    // ── CUSTOMIZE: identity and skill reference ──
    'You are a helpful AI assistant for <App Name>.',
    'Use the $<app-name>-data skill to access application data when the user asks about <domain>.',
    '',
    'RESPONSE FORMATS — pick the right one:',
    '',
    '1) TEXT (simple questions, greetings, explanations):',
    '   {"type":"message","text":"your **markdown** answer"}',
    '',
    '2) DASHBOARD (stats, summaries, counts, comparisons, overviews):',
    '   {"type":"dashboard","title":"Title","sections":[...]}',
    '   Section types:',
    '   - {"type":"widgets","items":[{"title":"Label","value":"42","subtext":"info"}]}',
    '   - {"type":"bars","label":"Title","items":[{"name":"X","value":10}]}',
    '   - {"type":"table","columns":["A","B"],"rows":[{"A":"x","B":"y"}]}',
    '   - {"type":"pills","items":[{"label":"Active","color":"green","count":5}]}',
    '   Combine multiple sections in one dashboard.',
    '',
    '3) CONFIRM (write/mutate operations):',
    '   {"type":"confirm","id":"unique_id","title":"Title","summary":"What happens","action":"command"}',
    '',
    'No markdown fences around the JSON.',
    'Use **bold** for names and key values. Never show raw IDs unless asked.',
    'Never dump raw output — always summarize nicely. Keep responses concise.',
    confirmedLine,
    '',
    `User: ${message}`,
  ].filter(Boolean).join('\n');
}

async function warmup() { await getCodex(); }
module.exports = { attachWebSocketServer, warmup };
```

---

## Step 3 — Build the Chat UI

The frontend handles the WebSocket protocol and renders three response types.
Adapt to the user's framework (React, Vue, Svelte, vanilla JS, etc.).

### WebSocket Protocol

Browser → Assistant:
- `{ type: "chat", message: "...", sessionId?: "..." }`
- `{ type: "reset", sessionId: "..." }`

Assistant → Browser:
- `session.id` → `{ sessionId }` — store for multi-turn
- `turn.started` → `{}` — show bouncing dots / spinner
- `agent.action` → `{ action, command, status }` — show thinking step
- `agent.text` → `{ text, status }` — update streaming text
- `turn.completed` → `{ text }` — parse response, render final UI
- `error` → `{ message }` — show error

### Response Parsing

On `turn.completed`, parse the final text as JSON:

```
function tryParseResponse(text) {
  try { return JSON.parse(text.trim()); } catch {}
  const first = text.indexOf('{');
  const last = text.lastIndexOf('}');
  if (first !== -1 && last > first) {
    try { return JSON.parse(text.slice(first, last + 1)); } catch {}
  }
  return null;
}

const parsed = tryParseResponse(finalText);
if (parsed?.type === 'dashboard')  → render generative UI sections
if (parsed?.type === 'confirm')    → render confirmation card
else                               → render parsed?.text || finalText as markdown
```

### Generative UI Sections

Render these based on the `sections` array in a dashboard response:

**widgets** — KPI cards (2–4 items with title, value, subtext)
**bars** — horizontal bar chart (name + value, auto-scaled)
**table** — columns + rows, styled inline table
**pills** — colored status badges (green, red, yellow, blue, orange)

### UX Patterns for Perceived Speed

1. On `turn.started` → show bouncing dots immediately
2. On `agent.action` → show "Working..." with live step labels
3. On `turn.completed` → animate text with typewriter effect (~8ms/char)
4. Only animate the latest message — older messages render instantly
5. Collapse thinking steps to "Ran N steps ▶" after completion

### Write Confirmation Flow

When the agent returns `type: "confirm"`, render a Confirm/Cancel card.
On confirm, send:
```
{ type: "chat", message: "CONFIRM_ACTION: <id>", sessionId: "..." }
```

---

## Step 4 — Run It

### Directory Structure

```
your-app/
├── .agents/
│   └── skills/
│       └── <app-name>/
│           └── SKILL.md              ← Agent discovers this automatically
├── assistant/
│   ├── package.json
│   ├── server.js
│   └── codex-bridge.js              ← Thin WebSocket relay
├── frontend/
│   └── ...                           ← Your chat UI component
└── ...
```

### Prerequisites

- Node.js 20+
- OpenAI API key (via `~/.codex/auth.json` or `OPENAI_API_KEY` env var)
- Your data source running and accessible

### Start

```bash
cd assistant && npm install

# Export whatever env vars your skill needs:
# export DATABASE_URL="postgresql://..."
# export API_BASE_URL="http://localhost:8000"
# export API_TOKEN="..."
export PROJECT_ROOT="$(cd .. && pwd)"

node server.js
```

Point your frontend WebSocket at `ws://localhost:3001/ws/codex`.

---

## Performance Checklist

| Technique | Type | Impact |
|-----------|------|--------|
| SDK pre-warming on server start | Actual | ~800ms saved on first message |
| `turn.started` before any async work | Perceived | <50ms to first visual feedback |
| Single unified skill (not per-entity) | Actual | Eliminates 1–2 extra agent turns |
| Bouncing dots animation | Perceived | Continuous visual feedback |
| Live thinking steps | Perceived | Progress visible before answer |
| Typewriter text animation | Perceived | Response feels interactive |
| Generative UI (not text walls) | Perceived | Instant scannability |

---

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Agent can't find skills | Set `workingDirectory` to your project root |
| Network commands fail in sandbox | Use `sandboxMode: 'danger-full-access'` |
| Agent dumps raw output | Add "Never dump raw output" to your prompt |
| Agent picks wrong response format | Add "WHEN TO USE DASHBOARD vs TEXT" examples to prompt |
| WebSocket reconnect storms | Nullify `onclose` before closing; debounce reconnects |
| First message is slow | Pre-warm SDK on server start with `warmup()` |
| Agent reads sensitive files | Add security boundaries to your SKILL.md |
| Docker Desktop on macOS | Run assistant on host; Codex sandbox has issues in Docker Desktop |

---

## Reference Implementation

The NexusLeads codebase has a full working implementation:

| File | Purpose |
|------|---------|
| `.agents/skills/plg-database/SKILL.md` | Data skill (PostgreSQL via psql) |
| `assistant/codex-bridge.js` | WebSocket relay with generative UI prompt |
| `assistant/server.js` | Express + WS server with SDK pre-warming |
| `frontend/src/components/ChatSidecar.tsx` | React chat UI with all UX patterns |
| `docs/chat-architecture.md` | Architecture documentation |
| `docs/chat-performance-design.md` | Performance and latency design |
