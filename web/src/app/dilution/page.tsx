import { desc, eq } from 'drizzle-orm';
import { db } from '@/lib/db';
import { scrapeRuns } from '@/lib/db/schema';
import { loadStandings } from '@/lib/analytics/data';
import { adminEnabled, isAdmin } from '@/lib/auth';
import { loadDrift } from '@/lib/analytics/drift';
import { markStaleRunsFailed } from '@/lib/scrape-cleanup';
import { DilutionContent } from './dilution-content';

export const dynamic = 'force-dynamic';

export default async function DilutionPage() {
  // Sweep zombie scrape_runs before reading (mirrors / page).
  await markStaleRunsFailed();

  const [rows, latestRunRows, lastSuccessRows, admin, drift] = await Promise.all([
    loadStandings(),
    db
      .select({
        id: scrapeRuns.id,
        startedAt: scrapeRuns.startedAt,
        finishedAt: scrapeRuns.finishedAt,
        status: scrapeRuns.status,
        errorMessage: scrapeRuns.errorMessage,
        leaguesProcessed: scrapeRuns.leaguesProcessed,
        leaguesFailed: scrapeRuns.leaguesFailed,
        standingsCount: scrapeRuns.standingsCount,
      })
      .from(scrapeRuns)
      .orderBy(desc(scrapeRuns.startedAt))
      .limit(1),
    db
      .select({
        finishedAt: scrapeRuns.finishedAt,
        standingsCount: scrapeRuns.standingsCount,
      })
      .from(scrapeRuns)
      .where(eq(scrapeRuns.status, 'success'))
      .orderBy(desc(scrapeRuns.finishedAt))
      .limit(1),
    isAdmin(),
    loadDrift(),
  ]);

  const latestRun = latestRunRows[0] ?? null;
  const lastSuccess = lastSuccessRows[0] ?? null;

  return (
    <DilutionContent
      rows={rows}
      drift={
        drift
          ? {
              ...drift,
              prevFinishedAt: drift.prevFinishedAt?.toISOString() ?? null,
              currFinishedAt: drift.currFinishedAt?.toISOString() ?? null,
            }
          : null
      }
      lastUpdated={
        lastSuccess
          ? {
              finishedAt: lastSuccess.finishedAt,
              standingsCount: lastSuccess.standingsCount,
            }
          : null
      }
      adminEnabled={adminEnabled()}
      isAdmin={admin}
      initialRun={
        latestRun
          ? {
              id: latestRun.id,
              startedAt: latestRun.startedAt?.toISOString() ?? null,
              finishedAt: latestRun.finishedAt?.toISOString() ?? null,
              status: latestRun.status,
              errorMessage: latestRun.errorMessage,
              leaguesProcessed: latestRun.leaguesProcessed,
              leaguesFailed: latestRun.leaguesFailed,
              standingsCount: latestRun.standingsCount,
            }
          : null
      }
    />
  );
}
