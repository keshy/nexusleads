const express = require('express');
const http = require('http');
const { attachWebSocketServer, warmup } = require('./codex-bridge');

const PORT = process.env.PORT || 3001;

const app = express();
app.get('/health', (_req, res) => res.json({ status: 'ok' }));

const server = http.createServer(app);
attachWebSocketServer(server);

server.listen(PORT, () => {
  console.log(`Assistant service listening on port ${PORT}`);
  warmup().then(() => console.log('[codex] SDK pre-warmed')).catch(() => {});
});
