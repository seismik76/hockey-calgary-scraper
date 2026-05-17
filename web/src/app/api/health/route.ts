import 'server-only';
import { NextResponse } from 'next/server';
import { sql } from 'drizzle-orm';
import { db } from '@/lib/db';
import { errorFields, log } from '@/lib/log';

export const dynamic = 'force-dynamic';

/**
 * Liveness + DB readiness check. Cheap enough for Render to hit every 30s.
 *
 * Returns 200 when the app process is up *and* a trivial query against
 * Postgres returns. Returns 503 if the DB ping fails — that's the signal we
 * want Render to interpret as "this instance is unhealthy, restart or stop
 * routing to it." The default `/` health check only proves the port is open
 * and Next.js cached a render; it'll happily serve stale data while
 * Postgres is unreachable.
 */
export async function GET() {
  const t0 = Date.now();
  try {
    await db.execute(sql`SELECT 1`);
    return NextResponse.json({
      ok: true,
      db: 'reachable',
      dbLatencyMs: Date.now() - t0,
    });
  } catch (e) {
    log.error('health.db_unreachable', errorFields(e));
    return NextResponse.json(
      { ok: false, db: 'unreachable', dbLatencyMs: Date.now() - t0 },
      { status: 503 },
    );
  }
}
