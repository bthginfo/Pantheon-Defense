import { randomBytes, scrypt as derive, createHash, timingSafeEqual } from 'node:crypto';
import { promisify } from 'node:util';
import { Conflict, create, mutate, read } from './store.mjs';
import { cookies, cookieName, HttpError, sessionHeader } from './http.mjs';
import { masteryPayment, materials, waveMaterials } from '../shared/progression.js';

const scrypt = promisify(derive);
const sessionSeconds = 60 * 60 * 24 * 21;
const dummySalt = '1eb7bc1ebed3240ec6a434a2070adc4b';
const attempts = new Map();

export const sha = text => createHash('sha256').update(text).digest('hex');
export const normalizedHandle = value => typeof value === 'string' ? value.toLowerCase().trim() : '';
export const validHandle = value => /^[a-z][a-z0-9_]{2,19}$/.test(value);

function guardRate(req, type, count) {
  const ip = String(req.headers['x-vercel-forwarded-for'] ?? req.socket?.remoteAddress ?? 'local')
    .split(',')[0].trim();
  const now = Date.now();
  const bucket = `${type}:${ip}`;
  const previous = attempts.get(bucket);
  const recent = previous?.until > now ? previous : { used: 0, until: now + 300_000 };
  if (recent.used >= count) throw new HttpError(429, 'Zu viele Versuche. Warte ein paar Minuten.');
  recent.used++;
  attempts.set(bucket, recent);
  if (attempts.size > 1800) for (const [key, item] of attempts) if (item.until < now) attempts.delete(key);
}

async function passwordHash(password, salt) {
  const hash = await scrypt(password, salt, 64, { N: 32768, r: 8, p: 1, maxmem: 64 * 1024 * 1024 });
  return hash.toString('hex');
}

export function level(xp) {
  return Math.min(12, 1 + Math.floor(Math.sqrt(xp / 140)));
}

function campaignRecord(account) {
  if (account.campaignWins) return account.campaignWins;
  const wins = {};
  for (const result of account.records ?? []) {
    if (result.won && result.challenge === 'campaign') {
      const rank = result.difficulty ?? 'normal';
      wins[rank] = (wins[rank] ?? 0) + 1;
    }
  }
  return wins;
}

export function publicAccount(account) {
  return {
    handle: account.handle,
    name: account.name,
    xp: account.xp,
    level: level(account.xp),
    matches: account.matches ?? [],
    records: account.records?.slice(0, 16) ?? [],
    badges: account.badges ?? [],
    seals: account.seals ?? 0,
    masteries: account.masteries ?? {},
    materials: Object.fromEntries(waveMaterials.map(key => [key, account.materials?.[key] ?? 0])),
    campaignWins: campaignRecord(account),
    fieldSigns: account.fieldSigns ?? {},
    fieldSign: account.fieldSign ?? null,
  };
}

async function issue(req, res, account) {
  const token = randomBytes(32).toString('base64url');
  await create(`session-${sha(token)}`, {
    handle: account.handle, validUntil: Date.now() + sessionSeconds * 1000, active: true,
  });
  res.setHeader('Set-Cookie', sessionHeader(req, token, sessionSeconds));
  return publicAccount(account);
}

export async function register(req, res, data) {
  guardRate(req, 'register', 16);
  const handle = normalizedHandle(data.handle);
  const name = typeof data.name === 'string' ? data.name.trim().normalize('NFC') : '';
  const password = data.password;
  if (!validHandle(handle)) throw new HttpError(400, 'Der Rufname braucht 3 bis 20 Zeichen. Erlaubt sind Buchstaben, Ziffern und _.');
  if (name.length < 2 || name.length > 30 || /[\x00-\x1f\x7f]/.test(name)) throw new HttpError(400, 'Gib einen Anzeigenamen mit 2 bis 30 Zeichen ein.');
  if (typeof password !== 'string' || password.length < 10 || password.length > 128) {
    throw new HttpError(400, 'Das Passwort braucht mindestens 10 Zeichen.');
  }
  const salt = randomBytes(16).toString('hex');
  const account = { handle, name, salt, hash: await passwordHash(password, salt), xp: 0,
    matches: [], records: [], badges: [], credited: [], created: Date.now() };
  try {
    await create(`account-${handle}`, account);
  } catch (error) {
    if (error instanceof Conflict) throw new HttpError(409, 'Dieser Rufname ist bereits vergeben.');
    throw error;
  }
  return issue(req, res, account);
}

export async function login(req, res, data) {
  guardRate(req, 'login', 28);
  const handle = normalizedHandle(data.handle);
  const sensible = validHandle(handle) && typeof data.password === 'string' && data.password.length <= 128;
  const account = sensible ? await read(`account-${handle}`) : undefined;
  const supplied = await passwordHash(sensible ? data.password : 'invalid password', account?.salt ?? dummySalt);
  const expected = account?.hash ?? '0'.repeat(128);
  const valid = timingSafeEqual(Buffer.from(supplied, 'hex'), Buffer.from(expected, 'hex'));
  if (!valid || !account) throw new HttpError(401, 'Rufname oder Passwort ist falsch.');
  return issue(req, res, account);
}

export async function identity(req, required = true) {
  const token = cookies(req)[cookieName] ?? '';
  const session = /^[A-Za-z0-9_-]{43}$/.test(token) ? await read(`session-${sha(token)}`) : undefined;
  if (session?.active && session.validUntil > Date.now()) return session.handle;
  if (required) throw new HttpError(401, 'Melde dich an, um fortzufahren.');
  return null;
}

export async function profile(handle) {
  const account = await read(`account-${handle}`);
  if (!account) throw new HttpError(401, 'Dieses Konto ist nicht mehr verfügbar.');
  return publicAccount(account);
}

export async function logout(req, res) {
  const token = cookies(req)[cookieName] ?? '';
  if (/^[A-Za-z0-9_-]{43}$/.test(token)) {
    await mutate(`session-${sha(token)}`, current => current?.active ? { ...current, active: false } : undefined);
  }
  res.setHeader('Set-Cookie', sessionHeader(req, '', 0));
}

export async function remember(handle, id) {
  await mutate(`account-${handle}`, account => {
    if (!account || account.matches.includes(id)) return undefined;
    return { ...account, matches: [id, ...account.matches].slice(0, 14) };
  });
}

export async function credit(handle, result) {
  await mutate(`account-${handle}`, account => {
    if (!account || account.credited?.includes(result.id)) return undefined;
    const badges = [...account.badges];
    for (const [condition, badge] of [
      [result.won, 'Erstes Banner'], [result.won && result.duo, 'Schulter an Schulter'],
      [result.won && result.challenge !== 'campaign', 'Prüfung bestanden'],
      [result.merges >= 3, 'Meister der Schmiede'], [result.casts >= 3, 'Stimme der Götter'],
    ]) {
      if (condition && !badges.includes(badge)) badges.push(badge);
    }
    const campaignWins = { ...campaignRecord(account) };
    if (result.won && result.challenge === 'campaign') {
      const rank = result.difficulty ?? 'normal';
      campaignWins[rank] = (campaignWins[rank] ?? 0) + 1;
    }
    const waveGrants = { ...account.waveGrants };
    delete waveGrants[result.id];
    return { ...account, xp: account.xp + result.xp, badges, campaignWins, waveGrants,
      seals: (account.seals ?? 0) + (result.seals ?? 0),
      records: [result, ...(account.records ?? [])].slice(0, 35),
      credited: [...(account.credited ?? []), result.id] };
  });
}

export async function creditWaves(handle, battle, treasury) {
  await mutate(`account-${handle}`, account => {
    if (!account || account.credited?.includes(battle)) return undefined;
    const previous = account.waveGrants?.[battle];
    if ((previous?.wave ?? 0) >= treasury.wave) return undefined;
    const balances = { ...account.materials };
    for (const material of waveMaterials) {
      const earned = (treasury.spoils[material] ?? 0) - (previous?.spoils[material] ?? 0);
      balances[material] = (balances[material] ?? 0) + Math.max(0, earned);
    }
    return { ...account, materials: balances,
      waveGrants: { ...account.waveGrants, [battle]: { wave: treasury.wave, spoils: treasury.spoils } } };
  });
}

export async function unlockMastery(handle, actor, expected, catalog) {
  const figure = catalog.find(item => item.id === actor);
  if (!figure) throw new HttpError(404, 'Diese Figur gibt es nicht.');
  const saved = await mutate(`account-${handle}`, account => {
    if (!account) throw new HttpError(401, 'Melde dich an, um fortzufahren.');
    if (level(account.xp) < figure.unlock) throw new HttpError(403, 'Diese Figur ist noch gesperrt.');
    const current = account.masteries?.[actor] ?? 0;
    if (current !== expected) throw new HttpError(409, 'Die Meisterschaft hat sich bereits geändert.');
    if (current >= 3) throw new HttpError(409, 'Die Meisterschaft ist vollständig ausgebaut.');
    const payment = masteryPayment(figure.kind, current, account.materials, account.seals);
    if (!payment.affordable) throw new HttpError(409, `Dafür fehlen dir ${materials[payment.material]}.`);
    const changed = payment.material === 'seals'
      ? { seals: account.seals - payment.amount }
      : { materials: { ...account.materials, [payment.material]: account.materials[payment.material] - payment.amount } };
    return { ...account, ...changed, masteries: { ...account.masteries, [actor]: current + 1 } };
  });
  return publicAccount(saved);
}

export async function changeFieldSign(handle, { id, action, expected }, signs) {
  const definition = signs.find(sign => sign.id === id);
  if (!definition && !(action === 'equip' && id === null)) throw new HttpError(404, 'Dieses Feldzeichen gibt es nicht.');
  const saved = await mutate(`account-${handle}`, account => {
    if (!account) throw new HttpError(401, 'Melde dich an, um fortzufahren.');
    const rank = account.fieldSigns?.[id] ?? 0;
    if (action === 'equip') {
      if (id && !rank) throw new HttpError(403, 'Schmiede dieses Feldzeichen zuerst.');
      return (account.fieldSign ?? null) === id ? undefined : { ...account, fieldSign: id };
    }
    if (action !== 'forge') throw new HttpError(400, 'Diese Feldzeichen-Aktion gibt es nicht.');
    if (expected !== rank || rank >= 2) throw new HttpError(409, 'Der Rang dieses Feldzeichens hat sich geändert.');
    const material = rank === 0 ? 'runedust' : 'cores';
    const price = rank === 0 ? definition.forge : definition.awaken;
    const balance = account.materials?.[material] ?? 0;
    if (balance < price) throw new HttpError(409, `Dafür fehlen dir ${materials[material]}.`);
    return { ...account, materials: { ...account.materials, [material]: balance - price },
      fieldSigns: { ...account.fieldSigns, [id]: rank + 1 }, fieldSign: account.fieldSign ?? id };
  });
  return publicAccount(saved);
}
