import { createReadStream } from 'node:fs';
import { createServer } from 'node:http';
import { createServer as viteServer } from 'vite';
import game from '../api/game.mjs';
import { attachRealtime } from '../server/realtime.mjs';

let vite;
const server = createServer((req, res) => {
  const path = new URL(req.url, 'http://localhost').pathname;
  if (path === '/api/game') return game(req, res);
  if (/^\/wasm\/arena(?:\.js|_bg\.wasm)$/.test(path)) {
    const file = createReadStream(new URL(`../public${path}`, import.meta.url));
    file.once('error', () => { res.statusCode = 404; res.end('Build the arena with npm run build.'); });
    file.once('open', () => {
      res.setHeader('Content-Type', path.endsWith('.wasm') ? 'application/wasm' : 'text/javascript');
      file.pipe(res);
    });
    return;
  }
  vite.middlewares(req, res);
});
vite = await viteServer({
  appType: 'spa', server: { middlewareMode: true, hmr: { server } },
});
attachRealtime(server);
server.listen(Number(process.env.PORT ?? 4173), '0.0.0.0', () => {
  console.log(`Pantheon Defense → http://localhost:${process.env.PORT ?? 4173}`);
});
