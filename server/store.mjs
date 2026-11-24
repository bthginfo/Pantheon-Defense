import { mkdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { get, head, put, BlobNotFoundError, BlobPreconditionFailedError } from '@vercel/blob';
import pg from 'pg';

export class Conflict extends Error {
  status = 409;
}
let connection;

async function connect() {
  const url = process.env.DATABASE_URL ?? process.env.POSTGRES_URL;
  if (url) {
    const pool = new pg.Pool({ connectionString: url, max: 4, idleTimeoutMillis: 10_000 });
    await pool.query('CREATE TABLE IF NOT EXISTS pantheon_document (key TEXT PRIMARY KEY, version INTEGER NOT NULL, body TEXT NOT NULL)');
    return {
      async read(key) {
        const { rows: [row] } = await pool.query('SELECT version, body FROM pantheon_document WHERE key = $1', [key]);
        return row && { version: row.version, value: JSON.parse(row.body) };
      },
      async write(key, version, value) {
        const body = JSON.stringify(value);
        const result = version === undefined
          ? await pool.query('INSERT INTO pantheon_document VALUES ($1,1,$2) ON CONFLICT DO NOTHING', [key, body])
          : await pool.query('UPDATE pantheon_document SET version=version+1, body=$3 WHERE key=$1 AND version=$2', [key, version, body]);
        if (!result.rowCount) throw new Conflict();
      },
    };
  }
  if (process.env.BLOB_READ_WRITE_TOKEN || process.env.BLOB_STORE_ID) {
    const path = key => `state/v1/${key}.json`;
    const documents = new Map();
    function remember(key, version, body) {
      documents.delete(key);
      documents.set(key, { version, body });
      if (documents.size > 32) documents.delete(documents.keys().next().value);
    }
    return {
      async read(key) {
        try {
          for (let attempt = 0; attempt < 4; attempt++) {
            const metadata = await head(path(key));
            if (!metadata.etag) throw new Error('The storage response did not return a document version.');
            const cached = documents.get(key);
            if (cached?.version === metadata.etag) {
              return { version: cached.version, value: JSON.parse(cached.body) };
            }
            // A versioned read keeps the document body and the conditional-write tag consistent.
            const url = new URL(metadata.url);
            url.searchParams.set('revision', metadata.etag);
            const response = await get(url.href, { access: 'private', useCache: false,
              headers: { 'Cache-Control': 'no-cache', 'Accept-Encoding': 'identity' } });
            if (!response || response.statusCode !== 200) continue;
            if (response.blob.etag === metadata.etag) {
              const body = await new Response(response.stream).text();
              const value = JSON.parse(body);
              remember(key, metadata.etag, body);
              return { version: metadata.etag, value };
            }
            await response.stream.cancel();
            await new Promise(resolve => setTimeout(resolve, 25 * (attempt + 1)));
          }
          throw new Conflict('Der Spielstand wird noch synchronisiert. Versuch es gleich nochmal.');
        } catch (error) {
          if (error instanceof BlobNotFoundError || error?.name === 'BlobNotFoundError') return undefined;
          throw error;
        }
      },
      async write(key, version, value) {
        try {
          const body = JSON.stringify(value);
          const saved = await put(path(key), body, {
            access: 'private', addRandomSuffix: false, contentType: 'application/json',
            allowOverwrite: version !== undefined, ...(version !== undefined && { ifMatch: version }),
          });
          if (saved.etag) remember(key, saved.etag, body);
        } catch (error) {
          if (error instanceof BlobPreconditionFailedError
              || (version === undefined && /already exists/i.test(error?.message ?? ''))) throw new Conflict();
          throw error;
        }
      },
    };
  }
  if (process.env.VERCEL) throw new Error('A persistent store is required for the deployment.');
  const { DatabaseSync } = await import('node:sqlite');
  const file = resolve(process.env.PANTHEON_LOCAL_DB ?? '.cache/pantheon.sqlite');
  await mkdir(dirname(file), { recursive: true });
  const db = new DatabaseSync(file);
  db.exec('PRAGMA journal_mode=WAL; PRAGMA busy_timeout=4000; CREATE TABLE IF NOT EXISTS document (key TEXT PRIMARY KEY, version INTEGER NOT NULL, body TEXT NOT NULL)');
  const read = db.prepare('SELECT version, body FROM document WHERE key=?');
  const insert = db.prepare('INSERT INTO document VALUES (?,1,?) ON CONFLICT DO NOTHING');
  const update = db.prepare('UPDATE document SET version=version+1, body=? WHERE key=? AND version=?');
  return {
    async read(key) {
      const row = read.get(key);
      return row && { version: row.version, value: JSON.parse(row.body) };
    },
    async write(key, version, value) {
      const body = JSON.stringify(value);
      const result = version === undefined ? insert.run(key, body) : update.run(body, key, version);
      if (!result.changes) throw new Conflict();
    },
  };
}

async function store() {
  connection ??= connect().catch(error => { connection = undefined; throw error; });
  return connection;
}

export async function read(key) {
  return (await (await store()).read(key))?.value;
}

export async function create(key, value) {
  await (await store()).write(key, undefined, value);
  return value;
}

export async function mutate(key, change) {
  const data = await store();
  for (let attempt = 0; attempt < 10; attempt++) {
    const previous = await data.read(key);
    const value = await change(previous?.value);
    if (value === undefined) return previous?.value;
    try {
      await data.write(key, previous?.version, value);
      return value;
    } catch (error) {
      if (!(error instanceof Conflict)) throw error;
      await new Promise(resolve => setTimeout(resolve, Math.min(50, 3 * (attempt + 1))));
    }
  }
  throw new Conflict('Der Spielstand wurde gleichzeitig geändert. Versuche es noch einmal.');
}
