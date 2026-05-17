import 'server-only';
import { open } from 'node:fs/promises';
import path from 'node:path';
import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

const TAIL_BYTES = 16 * 1024; // last ~16KB of the log — enough for several dozen lines
const MAX_LINES = 40;

/** Returns the tail of scrape_log.txt as an array of lines. Used by the
 *  client-side progress banner to surface what the running scrape is doing. */
export async function GET() {
  const logPath = path.resolve(process.cwd(), '..', 'scrape_log.txt');
  try {
    const fh = await open(logPath, 'r');
    try {
      const stat = await fh.stat();
      const start = Math.max(0, stat.size - TAIL_BYTES);
      const length = stat.size - start;
      const buf = Buffer.alloc(length);
      await fh.read(buf, 0, length, start);
      const text = buf.toString('utf8');
      const lines = text
        .split(/\r?\n/)
        .map((l) => l.trim())
        .filter((l) => l.length > 0);
      return NextResponse.json({
        lines: lines.slice(-MAX_LINES),
        mtime: stat.mtimeMs,
      });
    } finally {
      await fh.close();
    }
  } catch (e) {
    const err = e as NodeJS.ErrnoException;
    if (err.code === 'ENOENT') {
      return NextResponse.json({ lines: [], mtime: null });
    }
    return NextResponse.json(
      { error: err.message, lines: [], mtime: null },
      { status: 500 },
    );
  }
}
