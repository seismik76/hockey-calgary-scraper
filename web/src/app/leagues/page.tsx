import { desc, eq } from 'drizzle-orm';
import { db } from '@/lib/db';
import { scrapeRuns } from '@/lib/db/schema';
import { loadLeagueIndex } from '@/lib/analytics/data';
import { LeagueIndexContent } from './leagues-index-content';

export const dynamic = 'force-dynamic';

export default async function LeaguesIndexPage() {
  const [entries, lastSuccessRows] = await Promise.all([
    loadLeagueIndex(),
    db
      .select({
        finishedAt: scrapeRuns.finishedAt,
        standingsCount: scrapeRuns.standingsCount,
      })
      .from(scrapeRuns)
      .where(eq(scrapeRuns.status, 'success'))
      .orderBy(desc(scrapeRuns.finishedAt))
      .limit(1),
  ]);

  const lastSuccess = lastSuccessRows[0] ?? null;

  return (
    <LeagueIndexContent
      entries={entries}
      lastUpdated={
        lastSuccess
          ? {
              finishedAt: lastSuccess.finishedAt,
              standingsCount: lastSuccess.standingsCount,
            }
          : null
      }
    />
  );
}
