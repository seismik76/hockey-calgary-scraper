import 'server-only';
import { NextResponse } from 'next/server';
import { desc } from 'drizzle-orm';
import { db } from '@/lib/db';
import { scrapeRuns } from '@/lib/db/schema';
import { markStaleRunsFailed } from '@/lib/scrape-cleanup';

export const dynamic = 'force-dynamic';

export async function GET() {
  // Flip any zombie "running" rows to "failed" before reporting — the banner
  // polls this endpoint, so the cleanup propagates to the UI within one tick.
  await markStaleRunsFailed();

  const rows = await db
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
    .limit(1);

  return NextResponse.json({ latest: rows[0] ?? null });
}
