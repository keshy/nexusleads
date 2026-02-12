const { WebSocketServer } = require('ws');
const { Codex } = require('@openai/codex-sdk');

const projectRoot = process.env.PROJECT_ROOT || '/project';
const sessions = new Map();

function attachWebSocketServer(httpServer) {
  const wss = new WebSocketServer({ server: httpServer, path: '/ws/codex' });

  wss.on('connection', (ws) => {
    console.log('[ws] new connection');

    ws.on('close', () => console.log('[ws] connection closed'));

    ws.on('message', async (raw) => {
      let msg;
      try {
        msg = JSON.parse(raw.toString());
      } catch (err) {
        ws.send(JSON.stringify({ type: 'error', message: 'Invalid JSON' }));
        return;
      }

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
  const { message, token, orgId, sessionId, apiBaseUrl, confirmedActionId } = msg;

  if (!message) {
    ws.send(JSON.stringify({ type: 'error', message: 'Missing message' }));
    return;
  }
  if (!token) {
    ws.send(JSON.stringify({ type: 'error', message: 'Missing token' }));
    return;
  }

  let thread;
  let currentSessionId = sessionId;
  const session = sessionId ? sessions.get(sessionId) : null;

  const baseUrl = apiBaseUrl || process.env.PLG_API_BASE_URL || 'http://localhost:8000';

  const codex = new Codex({
    env: {
      PATH: process.env.PATH || '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
      HOME: process.env.HOME || '/tmp',
      PLG_ACCESS_TOKEN: token,
      PLG_ORG_ID: orgId || '',
      PLG_API_BASE_URL: baseUrl,
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
    currentSessionId = `codex_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  }

  const orgLine = orgId ? `Active org: ${orgId}` : 'Active org: (none)';
  const confirmedLine = confirmedActionId
    ? `User has confirmed action id: ${confirmedActionId}. Proceed with ONLY that action.`
    : 'No action has been confirmed yet.';

  const prompt = [
    'You are a helpful AI assistant for PLG Lead Sourcer (NexusLeads).',
    'You must only use the skills in .agents/skills to query or mutate data. Never access the database directly.',
    'If the user asks about projects, repositories, leads, jobs, settings, organizations, integrations, billing, users, or dashboard stats — use the corresponding $plg-*-api skills.',
    `You have a valid API bearer token in $PLG_ACCESS_TOKEN and optional org in $PLG_ORG_ID. Use $PLG_API_BASE_URL (currently ${baseUrl}) for all API calls.`,
    orgLine,
    confirmedLine,
    '',
    `User: ${message}`,
  ].join('\n');

  try {
    ws.send(JSON.stringify({ type: 'turn.started' }));
    ws.send(JSON.stringify({ type: 'session.id', sessionId: currentSessionId }));

    const streamed = await thread.runStreamed(prompt);
    let lastText = '';

    for await (const event of streamed.events) {
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

        // Command execution events
        if (item.type === 'command_execution') {
          const cmd = item.command || item.call?.command || '';
          ws.send(JSON.stringify({
            type: 'agent.action',
            action: 'command',
            command: cmd,
          }));
        }

        // Text / message events
        if (item.type === 'message' || item.type === 'reasoning') {
          const text =
            typeof item.content === 'string'
              ? item.content
              : Array.isArray(item.content)
                ? item.content
                    .filter((c) => c.type === 'output_text' || c.type === 'text')
                    .map((c) => c.text)
                    .join('')
                : '';
          if (text && text !== lastText) {
            lastText = text;
            ws.send(JSON.stringify({
              type: 'agent.text',
              text,
              status: event.type === 'item.completed' ? 'done' : 'streaming',
            }));
          }
        }
      }

      if (event.type === 'turn.completed') {
        ws.send(JSON.stringify({ type: 'turn.completed', text: lastText }));
      }

      if (event.type === 'turn.failed') {
        ws.send(JSON.stringify({
          type: 'error',
          message: event.error?.message || 'Turn failed',
        }));
      }
    }
  } catch (err) {
    console.error('[codex] error:', err);
    ws.send(JSON.stringify({
      type: 'error',
      message: err.message || 'Internal error',
    }));
  }
}

module.exports = { attachWebSocketServer };
