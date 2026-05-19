import { desc, eq } from 'drizzle-orm';
import { notFound } from 'next/navigation';
import { db } from '@/lib/db';
import { scrapeRuns } from '@/lib/db/schema';
import { loadAvailableSeasons, loadCommunityAggregates } from '@/lib/analytics/data';
import { CommunityStandingsContent } from './community-standings-content';

export const dynamic = 'force-dynamic';

const SUPPORTED_AGES = new Set(['u11', 'u13', 'u15']);

export default async function CommunityStandingsPage({
  params,
  searchParams,
}: {
  params: Promise<{ age: string }>;
  searchParams: Promise<{ season?: string }>;
}) {
  const { age: ageParam } = await params;
  const { season: seasonParam } = await searchParams;
  const age = ageParam.toLowerCase();
  if (!SUPPORTED_AGES.has(age)) notFound();

  const ageLabel = age.toUpperCase();

  // Resolve the season: default to the most recent one with eligible data
  // (>= 2025-2026), or honor an explicit ?season=... if it's in the list.
  const seasons = await loadAvailableSeasons(ageLabel);
  if (seasons.length === 0) {
    // No eligible data yet — still render the page with an empty state.
    const lastSuccessRows = await db
      .select({
        finishedAt: scrapeRuns.finishedAt,
        standingsCount: scrapeRuns.standingsCount,
      })
      .from(scrapeRuns)
      .where(eq(scrapeRuns.status, 'success'))
      .orderBy(desc(scrapeRuns.finishedAt))
      .limit(1);
    const lastSuccess = lastSuccessRows[0] ?? null;
    return (
      <CommunityStandingsContent
        age={ageLabel}
        season={null}
        seasons={[]}
        rows={[]}
        lastUpdated={
          lastSuccess
            ? { finishedAt: lastSuccess.finishedAt, standingsCount: lastSuccess.standingsCount }
            : null
        }
      />
    );
  }

  const season = seasonParam && seasons.includes(seasonParam) ? seasonParam : seasons[0];

  const [rows, lastSuccessRows] = await Promise.all([
    loadCommunityAggregates(ageLabel, season),
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
    <CommunityStandingsContent
      age={ageLabel}
      season={season}
      seasons={seasons}
      rows={rows}
      lastUpdated={
        lastSuccess
          ? { finishedAt: lastSuccess.finishedAt, standingsCount: lastSuccess.standingsCount }
          : null
      }
    />
  );
}
