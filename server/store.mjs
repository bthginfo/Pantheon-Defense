import { mkdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { get, put, BlobPreconditionFailedError } from '@vercel/blob';
import pg from 'pg';

export class Conflict extends Error {}
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
    return {
      async read(key) {
        try {
          const response = await get(path(key), { access: 'private', useCache: false });
          if (!response || response.statusCode !== 200) return undefined;
          const value = await new Response(response.stream).json();
          return { version: response.blob.etag, value };
        } catch (error) {
          if (error?.name === 'BlobNotFoundError') return undefined;
          throw error;
        }
      },
      async write(key, version, value) {
        try {
          await put(path(key), JSON.stringify(value), {
            access: 'private', addRandomSuffix: false, contentType: 'application/json',
            allowOverwrite: version !== undefined, ...(version !== undefined && { ifMatch: version }),
          });
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
