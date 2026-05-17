'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Body1,
  Button,
  Caption1,
  Dialog,
  DialogActions,
  DialogBody,
  DialogContent,
  DialogSurface,
  DialogTitle,
  Field,
  Input,
  Popover,
  PopoverSurface,
  PopoverTrigger,
  Radio,
  RadioGroup,
  Spinner,
  Tooltip,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import {
  LockClosed20Regular,
  LockOpen20Regular,
  Play20Filled,
} from '@fluentui/react-icons';

const useStyles = makeStyles({
  cluster: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: tokens.spacingHorizontalXS,
  },
  popoverBody: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacingVerticalM,
    minWidth: '240px',
    padding: tokens.spacingHorizontalS,
  },
  error: {
    color: '#b91c1c',
  },
  dialogBody: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacingVerticalL,
  },
  runningPill: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: tokens.spacingHorizontalS,
    padding: `${tokens.spacingVerticalXS} ${tokens.spacingHorizontalM}`,
    borderRadius: tokens.borderRadiusMedium,
    backgroundColor: tokens.colorNeutralBackground3,
    color: tokens.colorNeutralForeground2,
    fontSize: '13px',
    fontWeight: tokens.fontWeightSemibold,
  },
});

export type ScraperRun = {
  id: number;
  startedAt: string | null;
  finishedAt: string | null;
  status: string;
  errorMessage: string | null;
  leaguesProcessed: number | null;
  leaguesFailed: number | null;
  standingsCount: number | null;
};

type Props = {
  adminEnabled: boolean;
  initialIsAdmin: boolean;
  initialRun: ScraperRun | null;
};

export function AdminPanel({ adminEnabled, initialIsAdmin, initialRun }: Props) {
  const s = useStyles();
  const router = useRouter();
  const [isAdmin, setIsAdmin] = useState(initialIsAdmin);
  const [run, setRun] = useState<ScraperRun | null>(initialRun);
  const [popoverOpen, setPopoverOpen] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);

  const isRunning = run?.status === 'running';
  const prevStatusRef = useRef(run?.status);

  // Poll for status while a scrape is running. When the status flips to
  // success/failed, refresh server data so the top-bar badges and the page
  // bodies pick up the new dataset.
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
        // swallow transient errors; we'll retry on the next tick
      }
    };
    const id = setInterval(tick, 5000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [isRunning]);

  useEffect(() => {
    const prev = prevStatusRef.current;
    const cur = run?.status;
    prevStatusRef.current = cur;
    if (prev === 'running' && (cur === 'success' || cur === 'failed')) {
      router.refresh();
    }
  }, [run?.status, router]);

  if (!adminEnabled) return null;

  return (
    <span className={s.cluster}>
      {isRunning ? (
        <RunningPill run={run!} />
      ) : isAdmin ? (
        <>
          <Button
            appearance="primary"
            size="small"
            icon={<Play20Filled />}
            onClick={() => setDialogOpen(true)}
          >
            Run scraper
          </Button>
          <Tooltip content="Lock admin" relationship="label">
            <Button
              appearance="subtle"
              size="small"
              icon={<LockOpen20Regular />}
              aria-label="Lock admin"
              onClick={async () => {
                await fetch('/api/admin/lock', { method: 'POST' });
                setIsAdmin(false);
                router.refresh();
              }}
            />
          </Tooltip>
          <RunDialog
            open={dialogOpen}
            onClose={() => setDialogOpen(false)}
            onStarted={(r) => {
              setRun(r);
              setDialogOpen(false);
            }}
          />
        </>
      ) : (
        <UnlockPopover
          open={popoverOpen}
          onOpenChange={setPopoverOpen}
          onUnlocked={() => {
            setIsAdmin(true);
            setPopoverOpen(false);
            router.refresh();
          }}
        />
      )}
    </span>
  );
}

function RunningPill({ run }: { run: ScraperRun }) {
  const s = useStyles();
  return (
    <span className={s.runningPill} title={`Run #${run.id} started ${run.startedAt ?? ''}`}>
      <Spinner size="extra-tiny" />
      Scraping…
    </span>
  );
}

function UnlockPopover({
  open,
  onOpenChange,
  onUnlocked,
}: {
  open: boolean;
  onOpenChange: (next: boolean) => void;
  onUnlocked: () => void;
}) {
  const s = useStyles();
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit() {
    if (submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch('/api/admin/unlock', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      });
      if (res.ok) {
        setPassword('');
        onUnlocked();
      } else if (res.status === 401) {
        setError('Wrong password.');
      } else {
        setError('Unable to unlock.');
      }
    } catch {
      setError('Network error.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Popover open={open} onOpenChange={(_, data) => onOpenChange(data.open)}>
      <PopoverTrigger disableButtonEnhancement>
        <Tooltip content="Admin" relationship="label">
          <Button
            appearance="subtle"
            size="small"
            icon={<LockClosed20Regular />}
            aria-label="Admin"
          />
        </Tooltip>
      </PopoverTrigger>
      <PopoverSurface>
        <form
          className={s.popoverBody}
          onSubmit={(e) => {
            e.preventDefault();
            void submit();
          }}
        >
          <Field
            label="Admin password"
            validationState={error ? 'error' : 'none'}
            validationMessage={error ?? undefined}
          >
            <Input
              type="password"
              size="small"
              value={password}
              onChange={(_, data) => setPassword(data.value)}
              autoFocus
            />
          </Field>
          <Button
            appearance="primary"
            size="small"
            type="submit"
            disabled={submitting || password.length === 0}
          >
            {submitting ? 'Unlocking…' : 'Unlock'}
          </Button>
        </form>
      </PopoverSurface>
    </Popover>
  );
}

function RunDialog({
  open,
  onClose,
  onStarted,
}: {
  open: boolean;
  onClose: () => void;
  onStarted: (run: ScraperRun) => void;
}) {
  const s = useStyles();
  const [mode, setMode] = useState<'update' | 'reset'>('update');
  const [confirmed, setConfirmed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (submitting || !confirmed) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch('/api/scraper/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reset: mode === 'reset' }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError(body.error ?? 'Failed to start scraper.');
        setSubmitting(false);
        return;
      }
      // Fetch the freshly-created run row so the UI flips into "running"
      // mode immediately (no waiting for the next poll tick).
      const statusRes = await fetch('/api/scraper/status', { cache: 'no-store' });
      const statusBody = (await statusRes.json()) as { latest: ScraperRun | null };
      if (statusBody.latest) onStarted(statusBody.latest);
      setConfirmed(false);
      setMode('update');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(_, data) => !data.open && onClose()}>
      <DialogSurface>
        <DialogBody>
          <DialogTitle>Run scraper</DialogTitle>
          <DialogContent className={s.dialogBody}>
            <Body1>
              Pulls fresh data from Hockey Calgary, RAMP, and TeamLinkt. Typically takes
              10–15 minutes. The page will reflect the new data once the run completes.
            </Body1>
            <Field label="Mode">
              <RadioGroup
                value={mode}
                onChange={(_, data) => setMode(data.value as 'update' | 'reset')}
              >
                <Radio
                  value="update"
                  label="Update existing data"
                />
                <Radio
                  value="reset"
                  label="Full reset (drop everything and rebuild)"
                />
              </RadioGroup>
            </Field>
            <Caption1>
              {mode === 'update'
                ? 'Safe and additive — existing standings stay, new/changed rows upsert.'
                : 'Destructive — drops all rows before scraping. Use only if the DB is corrupted.'}
            </Caption1>
            <Field>
              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  cursor: 'pointer',
                }}
              >
                <input
                  type="checkbox"
                  checked={confirmed}
                  onChange={(e) => setConfirmed(e.target.checked)}
                />
                <Body1>I want to run the scraper now</Body1>
              </label>
            </Field>
            {error && <Body1 className={s.error}>{error}</Body1>}
          </DialogContent>
          <DialogActions>
            <Button appearance="secondary" onClick={onClose} disabled={submitting}>
              Cancel
            </Button>
            <Button
              appearance="primary"
              icon={<Play20Filled />}
              onClick={() => void submit()}
              disabled={submitting || !confirmed}
            >
              {submitting ? 'Starting…' : 'Run'}
            </Button>
          </DialogActions>
        </DialogBody>
      </DialogSurface>
    </Dialog>
  );
}
