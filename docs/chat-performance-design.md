# Chat Performance & Perceived Latency Design

This document describes the design decisions that minimize both **actual
latency** and **perceived latency** in the NexusLeads chat experience.

---

## The Latency Problem

AI chat systems have inherent latency from multiple sources:

| Stage | Typical Latency | Source |
|-------|----------------|--------|
| SDK module import | ~800ms | Dynamic `import()` of `@openai/codex-sdk` |
| Thread creation | ~200ms | Codex SDK thread initialization |
| LLM inference | 2–8s | OpenAI API round-trip + token generation |
| Tool execution | 0.5–2s | `psql` query + sandbox overhead |
| Multi-step reasoning | 5–15s | Agent may run 2–5 tool calls per turn |

**Total worst case: 10–25 seconds** from message send to final response.

The design goal is to make this feel like **2–3 seconds** through a
combination of actual speedups and perception tricks.

---

## Actual Latency Reductions

### 1. SDK Pre-warming

The Codex SDK is a large ESM module loaded via dynamic `import()`. On first
use, this adds ~800ms. We eliminate this by pre-warming on server start:

```javascript
// server.js — pre-warm immediately after listen
server.listen(PORT, () => {
  warmup().then(() => console.log('[codex] SDK pre-warmed'));
});

// codex-bridge.js — cache the module
let CodexModule = null;
async function getCodex() {
  if (!CodexModule) {
    CodexModule = await import('@openai/codex-sdk');
  }
  return CodexModule;
}
```

**Savings: ~800ms on first message.**

### 2. Direct Database Access (psql vs REST API)

The previous architecture routed data queries through REST API calls:

```
Agent → curl localhost:8000/api/projects → FastAPI → SQLAlchemy → Postgres → JSON → Agent
```

The current architecture queries Postgres directly:

```
Agent → psql localhost:5433 → Postgres → JSON → Agent
```

This eliminates HTTP overhead, serialization layers, and the FastAPI event
loop. Each query saves ~100–300ms.

**Savings: ~100–300ms per tool call, compounding across multi-step turns.**

### 3. Single Unified Skill

The old architecture had 7 separate API skills (projects, repos, leads,
dashboard, settings, users, organizations). The agent had to reason about
which skill to use and sometimes tried multiple.

The new architecture has a single `plg-database` skill with the full schema.
The agent can write precise SQL in one shot instead of discovering endpoints.

**Savings: eliminates 1–2 unnecessary tool calls per turn (~2–4s).**

### 4. Host Execution (macOS Local Dev)

The Codex SDK's Rust sandbox binary has SSE streaming issues inside Docker
Desktop on macOS. Running the assistant on the host eliminates the Docker
virtualization overhead and network translation layer.

**Savings: ~200–500ms per LLM streaming round-trip.**

---

## Perceived Latency Reductions

These techniques don't reduce actual processing time but make the experience
feel significantly faster.

### 5. Immediate `turn.started` Signal

The `turn.started` event is sent **before** any async work (SDK init, thread
creation, LLM call). This means the frontend shows the "thinking" state
within milliseconds of the user pressing Enter.

```javascript
// codex-bridge.js — FIRST thing in handleChat, before any await
safeSend(ws, { type: 'session.id', sessionId: currentSessionId });
safeSend(ws, { type: 'turn.started' });

// Now do the slow stuff
const { Codex } = await getCodex();
const thread = codex.startThread(threadOptions);
const streamed = await thread.runStreamed(prompt);
```

**Without this:** user sees nothing for 1–3 seconds after sending.
**With this:** bouncing dots appear in <50ms.

### 6. Bouncing Dots (Waiting State)

While the agent is processing, the message bubble shows animated bouncing
dots instead of an empty bubble or a static "Loading..." text:

```tsx
<span className="typing-dots flex gap-1">
  <span className="animate-bounce" style={{ animationDelay: '0ms' }} />
  <span className="animate-bounce" style={{ animationDelay: '150ms' }} />
  <span className="animate-bounce" style={{ animationDelay: '300ms' }} />
</span>
```

This provides continuous visual feedback that the system is working.

### 7. Live Thinking Steps

As the agent executes commands, each step appears in real-time with a
descriptive label:

```
⟳ Working
  ● Querying projects
  ● Querying repositories
```

The user sees progress even before the final answer arrives. Steps are
labeled with human-readable descriptions (not raw SQL):

```typescript
if (raw.includes('psql') && raw.includes('projects')) return 'Querying projects'
if (raw.includes('psql') && raw.includes('repositories')) return 'Querying repositories'
```

After completion, steps collapse to a compact summary:
```
▶ Ran 3 steps
```

Each step is expandable to show the raw command for transparency.

### 8. Typewriter Streaming Effect

The final response text animates character by character at 8ms per character
(~125 chars/second). This creates the illusion of the AI "typing" in
real-time, even though the full text is already available.

```typescript
const TYPEWRITER_MS = 8

// Only the latest bot message animates; older messages render instantly
const shouldAnimate = isLatestBot && msg.text && !typewriterDoneIds.has(msg.id)
```

Key design choices:
- **Only the latest message animates** — scrolling up shows completed text
- **HTML-aware** — walks DOM text nodes so markdown formatting appears correctly
- **Fires `onDone` callback** — marks the message as complete to prevent re-animation

### 9. Generative UI (Dashboard Rendering)

Instead of dumping a wall of text, structured data is rendered as visual
components that are immediately scannable:

| Component | Use Case | Perception Benefit |
|-----------|----------|-------------------|
| Widget cards | KPI metrics | Glanceable numbers, no reading required |
| Bar charts | Comparisons | Visual hierarchy, instant ranking |
| Tables | Detailed listings | Structured, scannable rows |
| Status pills | Status breakdowns | Color-coded, pre-attentive processing |

The agent decides the format based on the query type:
- "how many repos?" → widgets
- "show me my projects" → table + widgets
- "give me an overview" → widgets + bars + pills

This reduces cognitive load — the user gets the answer faster because the
visual format matches the question type.

---

## Latency Budget

With all optimizations applied, the typical latency breakdown is:

| Stage | Time | User Sees |
|-------|------|-----------|
| Message sent | 0ms | Message appears in chat |
| `turn.started` received | <50ms | Bouncing dots appear |
| First `agent.action` | 2–4s | "Querying projects" step appears |
| Additional actions | +0.5–2s each | More steps appear live |
| `agent.text` (done) | 4–10s | Typewriter starts |
| Typewriter completes | +1–3s | Full response visible |

**Perceived wait: <50ms** (bouncing dots appear almost instantly).
**Perceived progress: continuous** (thinking steps stream in real-time).
**Perceived response: 4–10s** (first text appears), but feels interactive
throughout because of the progressive disclosure.

---

## Future Optimizations

- **Thread pooling** — pre-create idle Codex threads to eliminate thread
  startup latency on first message
- **Speculative prefetch** — start common queries (e.g., project list) when
  the chat opens, cache results
- **Streaming text** — if the Codex SDK supports partial text streaming,
  pipe it directly to the typewriter instead of waiting for `item.completed`
- **Connection keep-alive** — reuse the Codex SDK client instance across
  messages instead of creating a new one per turn
- **Edge caching** — cache recent query results with short TTL to avoid
  re-querying for repeated questions
