const { WebSocketServer } = require('ws');
const path = require('path');

let CodexModule = null;

async function getCodex() {
  if (!CodexModule) {
    CodexModule = await import('@openai/codex-sdk');
  }
  return CodexModule;
}

const projectRoot = process.env.PROJECT_ROOT || path.resolve(__dirname, '..');
const sessions = new Map();

function safeSend(ws, data) {
  if (ws.readyState === 1 /* OPEN */) {
    ws.send(typeof data === 'string' ? data : JSON.stringify(data));
    return true;
  }
  console.log('[ws] cannot send, readyState:', ws.readyState);
  return false;
}

function attachWebSocketServer(httpServer) {
  const wss = new WebSocketServer({ server: httpServer, path: '/ws/codex' });

  wss.on('connection', (ws) => {
    console.log('[ws] new connection');

    ws.on('close', () => console.log('[ws] connection closed'));

    ws.on('message', async (raw) => {
      console.log('[ws] message received:', raw.toString().slice(0, 200));
      let msg;
      try {
        msg = JSON.parse(raw.toString());
      } catch (err) {
        ws.send(JSON.stringify({ type: 'error', message: 'Invalid JSON' }));
        return;
      }

      console.log('[ws] parsed type:', msg.type);
      if (msg.type === 'chat') {
        await handleChat(ws, msg);
      } else if (msg.type === 'reset') {
        if (msg.sessionId && sessions.has(msg.sessionId)) {
          sessions.delete(msg.sessionId);
        }
        ws.send(JSON.stringify({ type: 'session.reset' }));
      }
    });
  });
}

async function handleChat(ws, msg) {
  const { message, sessionId, confirmedActionId } = msg;

  if (!message || !message.trim()) {
    ws.send(JSON.stringify({ type: 'error', message: 'Message is required.' }));
    return;
  }

  // Send turn.started IMMEDIATELY to reduce perceived latency
  let currentSessionId = sessionId || `codex_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  safeSend(ws, { type: 'session.id', sessionId: currentSessionId });
  safeSend(ws, { type: 'turn.started' });

  try {
    const { Codex } = await getCodex();

    let thread;
    const session = sessionId ? sessions.get(sessionId) : null;

    const databaseUrl = process.env.DATABASE_URL || 'postgresql://plg_user:plg_password@localhost:5433/plg_lead_sourcer';

    const codex = new Codex({
      env: {
        PATH: process.env.PATH || '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
        HOME: process.env.HOME || '/tmp',
        DATABASE_URL: databaseUrl,
      },
    });

    const threadOptions = {
      workingDirectory: projectRoot,
      sandboxMode: 'danger-full-access',
      approvalPolicy: 'never',
      skipGitRepoCheck: true,
    };

    if (session && session.threadId) {
      thread = codex.resumeThread(session.threadId, threadOptions);
      currentSessionId = sessionId;
    } else {
      thread = codex.startThread(threadOptions);
    }

    const confirmedLine = confirmedActionId
      ? `User has confirmed action id: ${confirmedActionId}. Proceed with ONLY that action.`
      : '';

    const prompt = [
      'You are a helpful AI assistant for PLG Lead Sourcer (NexusLeads).',
      'Use the $plg-database skill to query the PostgreSQL database via psql when the user asks about projects, repositories, leads, contributors, jobs, settings, or dashboard stats.',
      '',
      'RESPONSE FORMATS — pick the right one:',
      '',
      '1) TEXT answer (for simple questions, greetings, explanations):',
      '   {"type":"message","text":"your **markdown** answer"}',
      '',
      '2) DASHBOARD answer (for stats, summaries, counts, comparisons, overviews):',
      '   {"type":"dashboard","title":"Dashboard Title","sections":[...]}',
      '   Section types:',
      '   - {"type":"widgets","items":[{"title":"Label","value":"42","subtext":"extra info"},...]}',
      '     Use for KPI cards: counts, totals, key metrics (2-4 items)',
      '   - {"type":"bars","label":"Chart Title","items":[{"name":"Label","value":10},...]}',
      '     Use for ranked lists, distributions, comparisons',
      '   - {"type":"table","columns":["Name","Status","Count"],"rows":[{"Name":"x","Status":"y","Count":1},...]}',
      '     Use for detailed listings with multiple columns',
      '   - {"type":"pills","items":[{"label":"Active","color":"green","count":5},{"label":"Inactive","color":"red","count":2}]}',
      '     Use for status breakdowns. Colors: green, red, yellow, blue, orange',
      '   You can combine multiple sections in one dashboard.',
      '',
      '3) CONFIRM answer (for write operations):',
      '   {"type":"confirm","id":"unique_id","title":"Short title","summary":"What will happen","sql":"THE SQL"}',
      '',
      'No markdown fences around the JSON.',
      '',
      'FORMATTING RULES for "text" fields:',
      '- Use **bold** for names, titles, and key values',
      '- Use bullet lists: `- **Label:** value`',
      '- Group items with ### headings',
      '- Never show raw UUIDs unless the user asks for IDs',
      '- Never dump raw database output — always summarize nicely',
      '- Keep responses concise and scannable',
      '',
      'WHEN TO USE DASHBOARD vs TEXT:',
      '- "show me my projects" → dashboard with table section',
      '- "how many repos?" → dashboard with widgets',
      '- "give me an overview" → dashboard with widgets + bars',
      '- "what is X?" → text message',
      '- "hello" → text message',
      confirmedLine,
      '',
      `User: ${message}`,
    ].filter(Boolean).join('\n');

    console.log('[codex] starting thread.runStreamed...');
    const streamed = await thread.runStreamed(prompt);
    let finalText = '';

    for await (const event of streamed.events) {
      console.log('[codex] event:', event.type);

      if (ws.readyState !== 1) {
        console.log('[codex] ws closed, aborting event loop');
        break;
      }

      if (event.type === 'thread.started') {
        sessions.set(currentSessionId, { threadId: event.thread_id });
      }

      if (
        event.type === 'item.started' ||
        event.type === 'item.updated' ||
        event.type === 'item.completed'
      ) {
        const item = event.item;
        if (!item) continue;

        if (item.type === 'agent_message') {
          const text = item.content || item.text || '';
          if (text) {
            finalText = text;
            safeSend(ws, {
              type: 'agent.text',
              text,
              status: event.type === 'item.completed' ? 'done' : 'streaming',
            });
          }
        } else if (item.type === 'command_execution' && event.type === 'item.started') {
          safeSend(ws, {
            type: 'agent.action',
            action: 'command',
            command: item.command || item.args?.join(' ') || '',
            status: 'started',
          });
        } else if (item.type === 'mcp_tool_call' && event.type === 'item.started') {
          safeSend(ws, {
            type: 'agent.action',
            action: 'tool_call',
            tool: item.tool_name || '',
            status: 'started',
          });
        }
      }

      if (event.type === 'turn.completed') {
        console.log('[codex] turn completed, finalText length:', finalText.length);
        safeSend(ws, {
          type: 'turn.completed',
          text: finalText,
          usage: event.usage || null,
        });
      }

      if (event.type === 'turn.failed') {
        console.log('[codex] turn failed:', event.error?.message);
        safeSend(ws, {
          type: 'error',
          message: event.error?.message || 'Turn failed',
        });
      }

      if (event.type === 'error') {
        console.log('[codex] error event:', event.message);
        safeSend(ws, {
          type: 'error',
          message: event.message || 'Stream error',
        });
      }
    }
  } catch (err) {
    console.error('[codex] error:', err);
    safeSend(ws, {
      type: 'error',
      message: err.message || 'Codex bridge error',
    });
  }
}

async function warmup() {
  await getCodex();
}

module.exports = { attachWebSocketServer, warmup };
