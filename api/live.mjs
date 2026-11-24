import { createServer } from 'node:http';
import { attachRealtime } from '../server/realtime.mjs';

const server = createServer((_req, res) => {
  res.writeHead(426, { 'Content-Type': 'text/plain; charset=utf-8' });
  res.end('WebSocket upgrade required');
});
attachRealtime(server);
export default server;
