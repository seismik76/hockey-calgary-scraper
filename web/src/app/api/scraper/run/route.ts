import 'server-only';
import { spawn } from 'node:child_process';
import { openSync } from 'node:fs';
import path from 'node:path';
import { NextResponse } from 'next/server';
import { desc, eq, gte } from 'drizzle-orm';
import { db } from '@/lib/db';
import { scrapeRuns } from '@/lib/db/schema';
import { adminEnabled, isAdmin } from '@/lib/auth';
import { errorFields, log } from '@/lib/log';

export const dynamic = 'force-dynamic';

// Rate-limit settings. Both are floors against accidental misuse — the cookie
// gate is the real auth boundary, but these prevent double-click / runaway
// scripts from flooding the queue.
const COOLDOWN_MS = 60_000; // refuse if another scrape started within this window
const HOURLY_CAP = 10; // total scrape_runs in the trailing hour (running, succeeded, failed)

function pythonBin(): string {
  return process.env.PYTHON_BIN ?? (process.platform === 'win32' ? 'python' : 'python3');
}

export async function POST(req: Request) {
  if (!adminEnabled()) {
    return NextResponse.json({ error: 'admin disabled' }, { status: 404 });
  }
  if (!(await isAdmin())) {
    log.warn('scraper.run.unauthorized');
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  }

  let body: { reset?: boolean };
  try {
    body = await req.json();
  } catch {
    body = {};
  }
  const reset = Boolean(body.reset);

  // 1. Block concurrent runs (the scraper writes status='running' on entry).
  const existing = await db
    .select({ id: scrapeRuns.id })
    .from(scrapeRuns)
    .where(eq(scrapeRuns.status, 'running'))
    .limit(1);
  if (existing.length > 0) {
    log.info('scraper.run.rejected', { reason: 'already_running', runId: existing[0].id });
    return NextResponse.json(
      { error: 'scrape already running', runId: existing[0].id },
      { status: 409 },
    );
  }

  // 2. Cooldown — refuse if anything was started recently (defends against
  //    double-click before the Python process has a chance to write its row).
  const latest = await db
    .select({ startedAt: scrapeRuns.startedAt })
    .from(scrapeRuns)
    .orderBy(desc(scrapeRuns.startedAt))
    .limit(1);
  if (latest[0]?.startedAt) {
    const elapsed = Date.now() - latest[0].startedAt.getTime();
    if (elapsed < COOLDOWN_MS) {
      log.info('scraper.run.rejected', { reason: 'cooldown', elapsedMs: elapsed });
      return NextResponse.json(
        {
          error: `cooldown — wait ${Math.ceil((COOLDOWN_MS - elapsed) / 1000)}s before triggering another scrape`,
        },
        { status: 429 },
      );
    }
  }

  // 3. Hourly cap.
  const hourAgo = new Date(Date.now() - 3_600_000);
  const recent = await db
    .select({ id: scrapeRuns.id })
    .from(scrapeRuns)
    .where(gte(scrapeRuns.startedAt, hourAgo));
  if (recent.length >= HOURLY_CAP) {
    log.warn('scraper.run.rejected', { reason: 'hourly_cap', count: recent.length });
    return NextResponse.json(
      { error: `hourly limit reached (${HOURLY_CAP}/hr)` },
      { status: 429 },
    );
  }

  // Resolve scraper.py relative to the web/ working dir.
  const scriptDir = path.resolve(process.cwd(), '..');
  const scriptPath = path.join(scriptDir, 'scraper.py');
  const logPath = path.join(scriptDir, 'scrape_log.txt');

  let logFd: number;
  try {
    logFd = openSync(logPath, 'a');
  } catch (e) {
    log.error('scraper.run.log_open_failed', { logPath, ...errorFields(e) });
    return NextResponse.json(
      { error: `failed to open log file: ${(e as Error).message}` },
      { status: 500 },
    );
  }

  const args = [scriptPath];
  if (reset) args.push('--reset');

  try {
    const child = spawn(pythonBin(), args, {
      cwd: scriptDir,
      stdio: ['ignore', logFd, logFd],
      detached: true,
      env: process.env,
    });
    child.unref();
    log.info('scraper.run.spawned', { reset, pid: child.pid });
  } catch (e) {
    log.error('scraper.run.spawn_failed', { reset, ...errorFields(e) });
    return NextResponse.json(
      { error: `failed to spawn scraper: ${(e as Error).message}` },
      { status: 500 },
    );
  }

  return NextResponse.json({ ok: true, reset });
}
