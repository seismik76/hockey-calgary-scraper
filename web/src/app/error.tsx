'use client';

import { useEffect } from 'react';
import { Body1, Button, LargeTitle, makeStyles, tokens } from '@fluentui/react-components';
import { ArrowClockwise20Regular } from '@fluentui/react-icons';

const useStyles = makeStyles({
  wrap: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '100vh',
    padding: tokens.spacingHorizontalXXL,
    backgroundColor: tokens.colorNeutralBackground2,
  },
  card: {
    backgroundColor: tokens.colorNeutralBackground1,
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    borderRadius: tokens.borderRadiusXLarge,
    boxShadow: tokens.shadow8,
    padding: `${tokens.spacingVerticalXXL} ${tokens.spacingHorizontalXXL}`,
    maxWidth: '560px',
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacingVerticalL,
    textAlign: 'center',
  },
  message: {
    color: tokens.colorNeutralForeground2,
  },
  digest: {
    fontFamily: 'var(--font-jetbrains-mono), ui-monospace, monospace',
    fontSize: '12px',
    color: tokens.colorNeutralForeground3,
    padding: tokens.spacingHorizontalS,
    backgroundColor: tokens.colorNeutralBackground3,
    borderRadius: tokens.borderRadiusMedium,
    wordBreak: 'break-all',
  },
  actions: {
    display: 'flex',
    gap: tokens.spacingHorizontalM,
    justifyContent: 'center',
  },
});

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const s = useStyles();

  useEffect(() => {
    // Surface to whatever Render's log aggregator picks up. The digest is the
    // ID you'd use to find the matching stack trace in the server logs.
    console.error('[error.tsx]', { message: error.message, digest: error.digest });
  }, [error]);

  return (
    <div className={s.wrap}>
      <div className={s.card}>
        <LargeTitle as="h1">Something broke</LargeTitle>
        <Body1 className={s.message}>
          The page hit an unexpected error. Try reloading; if it persists, check the server
          logs with the digest below.
        </Body1>
        {error.digest && <div className={s.digest}>digest: {error.digest}</div>}
        <div className={s.actions}>
          <Button icon={<ArrowClockwise20Regular />} appearance="primary" onClick={() => reset()}>
            Try again
          </Button>
          <Button appearance="secondary" onClick={() => (window.location.href = '/')}>
            Go to Analytics
          </Button>
        </div>
      </div>
    </div>
  );
}
