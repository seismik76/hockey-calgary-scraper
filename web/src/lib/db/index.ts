import 'server-only';
import { config } from 'dotenv';
import { resolve } from 'node:path';
import { Pool } from 'pg';
import { drizzle, type NodePgDatabase } from 'drizzle-orm/node-postgres';
import * as schema from './schema';

// Local dev pulls DATABASE_URL from the parent ../.env (shared with the Python
// scraper). In prod the host injects it directly into process.env, so this is
// a no-op there.
config({ path: resolve(process.cwd(), '..', '.env') });

declare global {
  var __pgPool: Pool | undefined;
  var __drizzleDb: NodePgDatabase<typeof schema> | undefined;
}

function buildDb(): NodePgDatabase<typeof schema> {
  const raw = process.env.DATABASE_URL;
  if (!raw) {
    throw new Error(
      'DATABASE_URL is not set. In dev, expected in ../.env. In prod, set it as an environment variable on the host.',
    );
  }
  const connectionString = raw.replace('postgresql+psycopg://', 'postgresql://');
  const pool = global.__pgPool ?? new Pool({ connectionString, max: 5 });
  if (process.env.NODE_ENV !== 'production') global.__pgPool = pool;
  return drizzle(pool, { schema });
}

// Lazy proxy: defers DATABASE_URL validation until first access. Without this,
// `next build` fails on the "Collecting page data" step because it imports the
// route modules — which import this — before env vars are available on hosts
// like Render where env is injected at runtime, not build time.
export const db = new Proxy({} as NodePgDatabase<typeof schema>, {
  get(_target, prop, receiver) {
    if (!global.__drizzleDb) global.__drizzleDb = buildDb();
    const value = Reflect.get(
      global.__drizzleDb as unknown as object,
      prop,
      receiver,
    );
    return typeof value === 'function'
      ? (value as (...args: unknown[]) => unknown).bind(global.__drizzleDb)
      : value;
  },
});
