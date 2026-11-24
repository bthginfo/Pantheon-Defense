import release from '../package.json' with { type: 'json' };
import { identity, login, logout, profile, register } from '../server/accounts.mjs';
import { acceptInvite, act, board, createMatch, matchList, renewInvite } from '../server/matches.mjs';
import { assertOrigin, body, failure, HttpError, respond } from '../server/http.mjs';

export default async function handle(req, res) {
  try {
    const url = new URL(req.url, 'http://localhost');
    const operation = url.searchParams.get('op');
    if (req.method === 'GET' && operation === 'health') {
      return respond(res, 200, { game: 'Pantheon Defense', version: release.version });
    }
    if (req.method === 'GET' && operation === 'session') {
      const user = await identity(req, false);
      return respond(res, 200, { user: user ? await profile(user) : null });
    }
    if (req.method === 'POST') assertOrigin(req);
    if (req.method === 'POST' && operation === 'register') return respond(res, 201, { user: await register(req, res, await body(req)) });
    if (req.method === 'POST' && operation === 'login') return respond(res, 200, { user: await login(req, res, await body(req)) });
    const user = await identity(req);
    if (req.method === 'GET' && operation === 'board') return respond(res, 200, await board(user, url.searchParams.get('id')));
    if (req.method === 'GET' && operation === 'rooms') return respond(res, 200, { rooms: await matchList(user) });
    if (req.method !== 'POST') throw new HttpError(405, 'Diese Methode ist hier nicht verfügbar.');
    const data = await body(req);
    if (operation === 'logout') {
      await logout(req, res);
      return respond(res, 200, { ok: true });
    }
    if (operation === 'new') return respond(res, 201, await createMatch(user, data));
    if (operation === 'accept') return respond(res, 200, await acceptInvite(user, data.invite));
    if (operation === 'invite') return respond(res, 200, { invite: await renewInvite(user, data.id) });
    if (operation === 'action') return respond(res, 200, await act(user, data.id, data));
    throw new HttpError(404, 'Diese Aktion gibt es nicht.');
  } catch (error) {
    failure(res, error);
  }
}
