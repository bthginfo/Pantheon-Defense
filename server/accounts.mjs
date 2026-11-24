import { randomBytes, scrypt as derive, createHash, timingSafeEqual } from 'node:crypto';
import { promisify } from 'node:util';
import { Conflict, create, mutate, read } from './store.mjs';
import { cookies, cookieName, HttpError, sessionHeader } from './http.mjs';

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

export function publicAccount(account) {
  return {
    handle: account.handle,
    name: account.name,
    xp: account.xp,
    level: level(account.xp),
    matches: account.matches ?? [],
    records: account.records?.slice(0, 16) ?? [],
    badges: account.badges ?? [],
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
    if (!account || account.credited.includes(result.id)) return undefined;
    const badges = [...account.badges];
    for (const [condition, badge] of [
      [result.won, 'Erstes Banner'], [result.won && result.duo, 'Schulter an Schulter'],
      [result.won && result.challenge !== 'campaign', 'Prüfung bestanden'],
      [result.merges >= 3, 'Meister der Schmiede'], [result.casts >= 3, 'Stimme der Götter'],
    ]) {
      if (condition && !badges.includes(badge)) badges.push(badge);
    }
    return { ...account, xp: account.xp + result.xp, badges,
      records: [result, ...account.records].slice(0, 35),
      credited: [...account.credited, result.id] };
  });
}
