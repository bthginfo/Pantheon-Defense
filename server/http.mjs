export class HttpError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

export const cookieName = 'pantheon_session';

export function cookies(req) {
  return Object.fromEntries((req.headers.cookie ?? '').split(';').filter(c => c.includes('='))
    .map(c => { const [k, ...v] = c.trim().split('='); return [k, v.join('=')]; }));
}

export function origin(req) {
  const host = req.headers.host ?? '';
  return `${process.env.VERCEL || req.socket?.encrypted ? 'https' : 'http'}://${host}`;
}

export function assertOrigin(req) {
  if (req.headers.origin && req.headers.origin !== origin(req)) {
    throw new HttpError(403, 'Diese Aktion ist nur auf Pantheon Defense verfügbar.');
  }
}

export function sessionHeader(req, token, maxAge) {
  const secure = process.env.VERCEL || req.socket?.encrypted ? '; Secure' : '';
  return `${cookieName}=${token}; Path=/; Max-Age=${maxAge}; HttpOnly; SameSite=Lax${secure}`;
}

export async function body(req) {
  if (req.body !== undefined) return typeof req.body === 'string' ? JSON.parse(req.body) : req.body;
  let buffer = '';
  for await (const chunk of req) {
    buffer += chunk;
    if (buffer.length > 16_384) throw new HttpError(413, 'Die Anfrage ist zu groß.');
  }
  try {
    return buffer ? JSON.parse(buffer) : {};
  } catch {
    throw new HttpError(400, 'Die Anfrage enthält ungültige Daten.');
  }
}

export function respond(res, status, value) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', 'private, no-store');
  res.end(JSON.stringify(value));
}

export function failure(res, error) {
  if (!(error instanceof HttpError)) console.error(error?.name, error?.message);
  respond(res, error.status ?? 500, {
    error: error.status ? error.message : 'Der Server konnte die Anfrage nicht abschließen.',
  });
}
