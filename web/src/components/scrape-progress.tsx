'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Body1, Caption1, Spinner, makeStyles, tokens } from '@fluentui/react-components';
import type { ScraperRun } from './admin-panel';

const useStyles = makeStyles({
  banner: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacingHorizontalL,
    padding: `${tokens.spacingVerticalM} ${tokens.spacingHorizontalL}`,
    backgroundColor: '#eff6ff',
    borderLeft: `4px solid #3b82f6`,
    borderRadius: tokens.borderRadiusLarge,
    color: '#1e3a8a',
  },
  body: {
    flex: 1,
    minWidth: 0,
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacingVerticalXXS,
  },
  headline: {
    color: '#1e3a8a',
    display: 'flex',
    alignItems: 'baseline',
    gap: tokens.spacingHorizontalS,
    fontVariantNumeric: 'tabular-nums',
  },
  elapsed: {
    fontWeight: tokens.fontWeightSemibold,
  },
  log: {
    color: '#1e40af',
    fontFamily: 'var(--font-jetbrains-mono), ui-monospace, monospace',
    fontSize: '12px',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
});

function formatElapsed(ms: number): string {
  if (ms < 0) ms = 0;
  const total = Math.floor(ms / 1000);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export function ScrapeProgressBanner({ initialRun }: { initialRun: ScraperRun | null }) {
  const s = useStyles();
  const router = useRouter();
  const [run, setRun] = useState<ScraperRun | null>(initialRun);
  const [latestLogLine, setLatestLogLine] = useState<string | null>(null);
  const [, setNow] = useState(() => Date.now());
  const prevStatusRef = useRef(run?.status);

  const isRunning = run?.status === 'running';

  // Status poll (every 5s while running)
  useEffect(() => {
    if (!isRunning) return;
    let cancelled = false;
    const tick = async () => {
      try {
        const res = await fetch('/api/scraper/status', { cache: 'no-store' });
        if (!res.ok) return;
        const data = (await res.json()) as { latest: ScraperRun | null };
        if (!cancelled) setRun(data.latest);
      } catch {
        /* swallow */
      }
    };
    const id = setInterval(tick, 5000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [isRunning]);

  // Log tail poll (every 5s while running, offset from status poll)
  useEffect(() => {
    if (!isRunning) return;
    let cancelled = false;
    const tick = async () => {
      try {
        const res = await fetch('/api/scraper/log', { cache: 'no-store' });
        if (!res.ok) return;
        const data = (await res.json()) as { lines: string[] };
        const last = data.lines[data.lines.length - 1];
        if (!cancelled && last) setLatestLogLine(last);
      } catch {
        /* swallow */
      }
    };
    void tick();
    const id = setInterval(tick, 5000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [isRunning]);

  // Tick "now" every second so elapsed time stays live without re-fetching.
  useEffect(() => {
    if (!isRunning) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [isRunning]);

  // When a run finishes, refresh server data so the new dataset propagates.
  useEffect(() => {
    const prev = prevStatusRef.current;
    const cur = run?.status;
    prevStatusRef.current = cur;
    if (prev === 'running' && (cur === 'success' || cur === 'failed')) {
      router.refresh();
    }
  }, [run?.status, router]);

  if (!isRunning || !run?.startedAt) return null;

  const elapsedMs = Date.now() - new Date(run.startedAt).getTime();

  return (
    <div className={s.banner} role="status" aria-live="polite">
      <Spinner size="tiny" />
      <div className={s.body}>
        <Body1 className={s.headline}>
          <strong>Scrape in progress</strong>
          <span className={s.elapsed}>{formatElapsed(elapsedMs)}</span>
          <Caption1 style={{ color: '#1e40af' }}>
            · started {new Date(run.startedAt).toLocaleTimeString()} · typically 10–15 min
          </Caption1>
        </Body1>
        {latestLogLine && (
          <Caption1 className={s.log} title={latestLogLine}>
            {latestLogLine}
          </Caption1>
        )}
      </div>
    </div>
  );
}
