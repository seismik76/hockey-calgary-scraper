import 'server-only';
import { config } from 'dotenv';
import { resolve } from 'node:path';
import { Pool } from 'pg';
import { drizzle } from 'drizzle-orm/node-postgres';
import * as schema from './schema';

config({ path: resolve(process.cwd(), '..', '.env') });

const raw = process.env.DATABASE_URL;
if (!raw) {
  throw new Error(
    'DATABASE_URL is not set. Expected it in the parent ../.env (shared with the Python scraper).',
  );
}

const connectionString = raw.replace('postgresql+psycopg://', 'postgresql://');

declare global {
  var __pgPool: Pool | undefined;
}

const pool =
  global.__pgPool ?? new Pool({ connectionString, max: 5 });
if (process.env.NODE_ENV !== 'production') global.__pgPool = pool;

export const db = drizzle(pool, { schema });
