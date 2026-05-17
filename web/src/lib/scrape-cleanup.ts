import 'server-only';
import { and, eq, lt } from 'drizzle-orm';
import { db } from './db';
import { scrapeRuns } from './db/schema';
import { log } from './log';

// A scrape that hasn't finalised within this many ms is presumed dead — the
// container almost certainly got redeployed mid-run. We flip those rows to
// status='failed' so the UI stops showing a permanent "scrape in progress"
// banner and the rate-limit / "already running" checks don't get wedged.
//
// Real scrapes take 10–15 min, so 30 min is generous without being so long
// that a genuine zombie sits visible for hours.
const STALE_THRESHOLD_MS = 30 * 60 * 1000;

/** Marks any `running` scrape_runs older than the threshold as `failed`.
 *  Returns the number of rows updated (usually 0). Cheap when there's nothing
 *  to clean — a single bounded UPDATE.
 *
 *  Call from any read path that surfaces scrape state: the server pages,
 *  /api/scraper/status, /api/scraper/run (before the "already running"
 *  check). Safe to call concurrently — Postgres serialises the update. */
export async function markStaleRunsFailed(): Promise<number> {
  const cutoff = new Date(Date.now() - STALE_THRESHOLD_MS);
  try {
    const result = await db
      .update(scrapeRuns)
      .set({
        status: 'failed',
        finishedAt: new Date(),
        errorMessage:
          'process died before finalising (likely container restart or redeploy)',
      })
      .where(and(eq(scrapeRuns.status, 'running'), lt(scrapeRuns.startedAt, cutoff)))
      .returning({ id: scrapeRuns.id });

    if (result.length > 0) {
      log.warn('scraper.stale_runs_cleared', {
        count: result.length,
        ids: result.map((r) => r.id),
        thresholdMs: STALE_THRESHOLD_MS,
      });
    }
    return result.length;
  } catch (e) {
    // Don't let a cleanup failure block whatever called us — just log it.
    log.error('scraper.stale_cleanup_failed', {
      error: e instanceof Error ? e.message : String(e),
    });
    return 0;
  }
}
