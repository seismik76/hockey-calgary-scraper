import { config } from 'dotenv';
import { resolve } from 'node:path';
import type { Config } from 'drizzle-kit';

config({ path: resolve(process.cwd(), '..', '.env') });

const raw = process.env.DATABASE_URL;
if (!raw) throw new Error('DATABASE_URL not set in parent ../.env');

export default {
  schema: './src/lib/db/schema.ts',
  out: './drizzle',
  dialect: 'postgresql',
  dbCredentials: {
    url: raw.replace('postgresql+psycopg://', 'postgresql://'),
  },
} satisfies Config;
