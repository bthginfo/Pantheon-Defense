import { readFileSync } from 'node:fs';
import { randomBytes, randomUUID, timingSafeEqual } from 'node:crypto';
import core from './generated/simulation.js';
import { create, mutate, read } from './store.mjs';
import { credit, normalizedHandle, profile, remember, sha, validHandle } from './accounts.mjs';
import { HttpError } from './http.mjs';

export const catalog = JSON.parse(readFileSync(new URL('../public/assets/catalog.json', import.meta.url), 'utf8'));
const finished = game => game.phase === 'won' || game.phase === 'lost';
const active = game => game.phase === 'prep' || game.phase === 'combat';
const roomId = /^[a-f0-9-]{36}$/;
const key = id => `match-${id}`;

async function getRoom(id) {
  if (!roomId.test(id ?? '')) throw new HttpError(404, 'Diese Partie gibt es nicht.');
  const room = await read(key(id));
  if (!room) throw new HttpError(404, 'Diese Partie gibt es nicht.');
  return room;
}

function playerIndex(room, handle) {
  if (room.host.handle === handle) return 0;
  if (room.guest?.handle === handle && room.joined) return 1;
  throw new HttpError(403, 'Dein Konto gehört zu einem anderen Spielraum.');
}

function advance(room, now) {
  if (!active(room.game)) return room;
  const end = Math.min(now, room.liveUntil);
  const elapsed = Math.max(0, Math.floor((end - room.clockMs) / 50));
  if (!elapsed) return room;
  let game = room.game;
  let ticks = elapsed;
  while (ticks > 0 && active(game)) {
    const step = Math.min(ticks, 2400);
    game = JSON.parse(core.advance_game(JSON.stringify(game), step));
    ticks -= step;
  }
  return { ...room, game, clockMs: room.clockMs + elapsed * 50 };
}

function visible(room, handle) {
  return {
    id: room.id, host: room.host, guest: room.guest, joined: room.joined,
    viewer: playerIndex(room, handle), game: room.game, version: room.version,
  };
}

export async function createMatch(handle, data) {
  const host = await profile(handle);
  const theme = catalog.themes.find(item => item.id === data.theme);
  const challenge = catalog.challenges.find(item => item.id === data.challenge);
  if (!theme || !challenge || Math.max(theme.unlock, challenge.unlock) > host.level) {
    throw new HttpError(403, 'Diese Karte oder Prüfung ist noch gesperrt.');
  }
  const duo = data.mode === 'duo';
  const guestHandle = normalizedHandle(data.friend);
  if (duo && (!validHandle(guestHandle) || guestHandle === handle)) throw new HttpError(400, 'Gib den Rufnamen eines anderen registrierten Kontos ein.');
  const guest = duo ? await profile(guestHandle).catch(error => {
    if (error.status === 401) throw new HttpError(404, 'Diesen Rufnamen gibt es noch nicht.');
    throw error;
  }) : null;
  const id = randomUUID();
  const token = duo ? randomBytes(24).toString('base64url') : undefined;
  const game = JSON.parse(core.create_game(JSON.stringify({
    theme: theme.id, challenge: challenge.id, levels: guest ? [host.level, guest.level] : [host.level],
    masteries: guest ? [host.masteries, guest.masteries] : [host.masteries],
    seed: randomBytes(4).readUInt32LE(),
  })));
  const room = {
    id, host: { handle: host.handle, name: host.name }, guest: guest && { handle: guest.handle, name: guest.name },
    joined: !duo, inviteHash: token && sha(token), inviteExpiry: Date.now() + 86_400_000,
    game, clockMs: Date.now(), liveUntil: Date.now() + 30_000, version: 1,
    lastWrite: Date.now(), receipts: [], credited: false,
  };
  await create(key(id), room);
  await remember(handle, id);
  return { ...visible(room, handle), invite: token && `${id}.${token}` };
}

export async function renewInvite(handle, id) {
  const room = await getRoom(id);
  const token = randomBytes(24).toString('base64url');
  await mutate(key(room.id), current => {
    if (current.host.handle !== handle || !current.guest || current.joined || current.game.phase !== 'lobby') {
      throw new HttpError(403, 'Diese Einladung ist bereits eingelöst.');
    }
    return { ...current, inviteHash: sha(token), inviteExpiry: Date.now() + 86_400_000, version: current.version + 1 };
  });
  return `${id}.${token}`;
}

export async function acceptInvite(handle, invitation) {
  if (typeof invitation !== 'string') throw new HttpError(400, 'Der Einladungslink ist ungültig.');
  const [id, token, extra] = invitation.split('.');
  if (extra || !/^[A-Za-z0-9_-]{32}$/.test(token ?? '')) throw new HttpError(400, 'Der Einladungslink ist ungültig.');
  await getRoom(id);
  const room = await mutate(key(id), current => {
    const hash = sha(token);
    if (current.guest?.handle !== handle || !current.inviteHash ||
        !timingSafeEqual(Buffer.from(hash), Buffer.from(current.inviteHash))) {
      throw new HttpError(403, 'Diese Einladung gehört zu einem anderen Konto.');
    }
    if (current.joined) return undefined;
    if (current.inviteExpiry < Date.now()) throw new HttpError(410, 'Die Einladung ist abgelaufen.');
    return { ...current, joined: true, version: current.version + 1 };
  });
  await remember(handle, room.id);
  return visible(room, handle);
}

async function award(room) {
  if (room.credited || !finished(room.game)) return;
  const { game } = room;
  const challenge = catalog.challenges.find(item => item.id === game.challenge);
  const won = game.phase === 'won';
  // Leaving the lobby cannot award XP.
  const xp = game.wave ? Math.round((game.wave * 20 + Math.min(game.kills, 300) + (won ? 190 : 0)) * (challenge?.reward ?? 1)) : 0;
  const seals = won ? (game.challenge === 'campaign' ? 2 : 3) : game.wave >= 5 ? 1 : 0;
  for (const [index, member] of [room.host, room.joined ? room.guest : null].entries()) {
    if (!member) continue;
    const player = game.players[index];
    await credit(member.handle, {
      id: room.id, theme: game.theme, challenge: game.challenge, wave: game.wave, won, xp, seals,
      kills: game.kills, merges: player.merges, casts: player.casts, duo: Boolean(room.guest),
      completed: new Date().toISOString(),
    });
  }
  await mutate(key(room.id), current => current.credited ? undefined : { ...current, credited: true });
}

export async function board(handle, id) {
  const stored = await getRoom(id);
  playerIndex(stored, handle);
  const now = Date.now();
  let room = advance(stored, now);
  if ((!stored.credited && finished(room.game)) || (active(room.game) && now - stored.lastWrite > 14_000)) {
    room = await mutate(key(id), saved => {
      const next = advance(saved, now);
      if (finished(next.game) && finished(saved.game)) return undefined;
      if (!finished(next.game) && now - saved.lastWrite <= 14_000) return undefined;
      return {
        ...next, clockMs: Math.max(next.clockMs, now > saved.liveUntil ? now : next.clockMs),
        liveUntil: now + 35_000, lastWrite: now, version: saved.version + 1,
      };
    });
    room = advance(room, now);
    if (finished(room.game)) await award(room);
  }
  return visible(room, handle);
}

export async function act(handle, id, data) {
  await getRoom(id);
  const command = data.command;
  const nonce = data.nonce;
  if (!command || typeof command.type !== 'string' || !/^[a-f0-9-]{36}$/.test(nonce ?? '')) {
    throw new HttpError(400, 'Die Aktion ist ungültig.');
  }
  const room = await mutate(key(id), saved => {
    const player = playerIndex(saved, handle);
    const receipt = `${player}:${nonce}`;
    if (saved.receipts.includes(receipt)) return undefined;
    if (command.type === 'start' && saved.guest && !saved.joined) {
      throw new HttpError(409, 'Dein Mitspieler ist noch nicht beigetreten.');
    }
    const now = Date.now();
    const projected = advance(saved, now);
    let game;
    try {
      game = JSON.parse(core.apply_action(JSON.stringify(projected.game), player, JSON.stringify(command)));
    } catch (error) {
      const message = error.message.startsWith('invalid ') || error.message.includes('unknown variant')
        ? 'Diese Aktion konnte nicht gelesen werden.' : error.message;
      throw new HttpError(409, message);
    }
    return { ...projected, game, clockMs: (saved.game.phase === 'lobby' || now > saved.liveUntil) ? now : projected.clockMs,
      liveUntil: now + 35_000, lastWrite: now, version: saved.version + 1,
      receipts: [...saved.receipts.slice(-95), receipt] };
  });
  if (finished(room.game)) await award(room);
  return visible(room, handle);
}

export async function matchList(handle) {
  const account = await profile(handle);
  const rooms = await Promise.all(account.matches.slice(0, 8).map(id => getRoom(id).catch(error => {
    if (error.status === 404) return null;
    throw error;
  })));
  return rooms.filter(Boolean).map(room => ({
    id: room.id, theme: room.game.theme, mode: room.guest ? 'duo' : 'solo', joined: room.joined,
    phase: room.game.phase, wave: room.game.wave, challenge: room.game.challenge, partner: room.guest?.name,
  }));
}
