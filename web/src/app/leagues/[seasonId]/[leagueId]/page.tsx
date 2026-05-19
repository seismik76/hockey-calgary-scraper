import { desc, eq } from 'drizzle-orm';
import { notFound } from 'next/navigation';
import { db } from '@/lib/db';
import { scrapeRuns } from '@/lib/db/schema';
import { loadLeagueDetail, loadLeagueGames } from '@/lib/analytics/data';
import { LeagueDetailContent } from './league-detail-content';

export const dynamic = 'force-dynamic';

type Params = { seasonId: string; leagueId: string };

export default async function LeagueDetailPage({
  params,
}: {
  params: Promise<Params>;
}) {
  const { seasonId, leagueId } = await params;
  const sid = Number(seasonId);
  const lid = Number(leagueId);
  if (!Number.isInteger(sid) || !Number.isInteger(lid)) notFound();

  const [detail, games, lastSuccessRows] = await Promise.all([
    loadLeagueDetail(sid, lid),
    loadLeagueGames(sid, lid),
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

  if (!detail) notFound();

  const lastSuccess = lastSuccessRows[0] ?? null;

  // Pre-serialize Date values so they survive the server -> client component boundary.
  const serializedGames = games.map((g) => ({
    ...g,
    playedAt: g.playedAt ? g.playedAt.toISOString() : null,
  }));

  return (
    <LeagueDetailContent
      detail={detail}
      games={serializedGames}
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
