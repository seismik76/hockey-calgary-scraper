import 'server-only';
import { NextResponse } from 'next/server';
import { desc } from 'drizzle-orm';
import { db } from '@/lib/db';
import { scrapeRuns } from '@/lib/db/schema';

export const dynamic = 'force-dynamic';

export async function GET() {
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
