import 'server-only';
import { spawn } from 'node:child_process';
import { openSync } from 'node:fs';
import path from 'node:path';
import { NextResponse } from 'next/server';
import { eq } from 'drizzle-orm';
import { db } from '@/lib/db';
import { scrapeRuns } from '@/lib/db/schema';
import { adminEnabled, isAdmin } from '@/lib/auth';

export const dynamic = 'force-dynamic';

function pythonBin(): string {
  return process.env.PYTHON_BIN ?? (process.platform === 'win32' ? 'python' : 'python3');
}

export async function POST(req: Request) {
  if (!adminEnabled()) {
    return NextResponse.json({ error: 'admin disabled' }, { status: 404 });
  }
  if (!(await isAdmin())) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  }

  let body: { reset?: boolean };
  try {
    body = await req.json();
  } catch {
    body = {};
  }
  const reset = Boolean(body.reset);

  // Refuse to spawn a second scrape if one is already running. The DB is the
  // source of truth — the scraper inserts a row with status='running' before
  // doing any work and finalises it at the end.
  const existing = await db
    .select({ id: scrapeRuns.id })
    .from(scrapeRuns)
    .where(eq(scrapeRuns.status, 'running'))
    .limit(1);
  if (existing.length > 0) {
    return NextResponse.json(
      { error: 'scrape already running', runId: existing[0].id },
      { status: 409 },
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
  } catch (e) {
    return NextResponse.json(
      { error: `failed to spawn scraper: ${(e as Error).message}` },
      { status: 500 },
    );
  }

  return NextResponse.json({ ok: true, reset });
}
