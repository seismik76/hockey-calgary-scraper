import 'server-only';
import { desc, eq } from 'drizzle-orm';
import { db } from '@/lib/db';
import { scrapeRuns } from '@/lib/db/schema';

export type Drift = {
  /** Negative number; rows lost vs prior scrape. */
  delta: number;
  /** Fraction in (-1, 0); e.g. -0.08 = 8% drop. */
  pct: number;
  prevCount: number;
  currCount: number;
  prevFinishedAt: Date | null;
  currFinishedAt: Date | null;
};

const DRIFT_THRESHOLD = -0.05; // 5% drop

/** Returns drift info if the latest successful scrape's standings count dropped
 *  by more than 5% vs the previous successful scrape. Null otherwise. */
export async function loadDrift(): Promise<Drift | null> {
  const rows = await db
    .select({
      standingsCount: scrapeRuns.standingsCount,
      finishedAt: scrapeRuns.finishedAt,
    })
    .from(scrapeRuns)
    .where(eq(scrapeRuns.status, 'success'))
    .orderBy(desc(scrapeRuns.finishedAt))
    .limit(2);

  if (rows.length < 2) return null;
  const [curr, prev] = rows;
  if (!curr.standingsCount || !prev.standingsCount) return null;

  const delta = curr.standingsCount - prev.standingsCount;
  const pct = delta / prev.standingsCount;
  if (pct > DRIFT_THRESHOLD) return null;

  return {
    delta,
    pct,
    prevCount: prev.standingsCount,
    currCount: curr.standingsCount,
    prevFinishedAt: prev.finishedAt,
    currFinishedAt: curr.finishedAt,
  };
}
