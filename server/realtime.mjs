import { WebSocketServer, WebSocket } from 'ws';
import { identity } from './accounts.mjs';
import { board } from './matches.mjs';
import { assertOrigin } from './http.mjs';

export function attachRealtime(server) {
  const websocket = new WebSocketServer({ noServer: true, maxPayload: 4096 });
  server.on('upgrade', async (req, socket, head) => {
    socket.on('error', () => socket.destroy());
    try {
      const url = new URL(req.url, 'http://localhost');
      if (url.pathname !== '/api/live') return socket.destroy();
      assertOrigin(req);
      const handle = await identity(req);
      const id = url.searchParams.get('id');
      const initial = await board(handle, id);
      if (socket.destroyed) return;
      websocket.handleUpgrade(req, socket, head, ws => {
        ws.send(JSON.stringify(initial));
        let busy = false;
        let last = `${initial.version}:${initial.game.tick}`;
        let checks = 0;
        const timer = setInterval(async () => {
          if (busy || ws.readyState !== WebSocket.OPEN || ws.bufferedAmount > 250_000) return;
          busy = true;
          try {
            if (++checks % 32 === 0 && await identity(req) !== handle) return ws.close(1008);
            const packet = await board(handle, id);
            const revision = `${packet.version}:${packet.game.tick}`;
            if (revision !== last) {
              last = revision;
              ws.send(JSON.stringify(packet));
            }
            if (packet.game.phase === 'won' || packet.game.phase === 'lost') clearInterval(timer);
          } catch (error) {
            ws.close(error.status === 401 || error.status === 403 ? 1008 : 1011);
          } finally { busy = false; }
        }, 650);
        ws.once('close', () => clearInterval(timer));
        ws.once('error', () => ws.terminate());
      });
    } catch (error) {
      const status = error.status ?? 503;
      if (!socket.destroyed) socket.end(`HTTP/1.1 ${status} Connection Rejected\r\nConnection: close\r\n\r\n`);
    }
  });
  return websocket;
}
