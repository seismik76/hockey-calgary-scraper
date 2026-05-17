'use client';

import { useState } from 'react';
import { Body1, Button, makeStyles, tokens } from '@fluentui/react-components';
import { Dismiss20Regular, Warning24Filled } from '@fluentui/react-icons';
import type { Drift } from '@/lib/analytics/drift';

const useStyles = makeStyles({
  banner: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: tokens.spacingHorizontalM,
    padding: `${tokens.spacingVerticalM} ${tokens.spacingHorizontalL}`,
    backgroundColor: '#fef3c7',
    borderLeft: `4px solid #f59e0b`,
    borderRadius: tokens.borderRadiusLarge,
    color: '#78350f',
  },
  icon: {
    color: '#b45309',
    flexShrink: 0,
    marginTop: '2px',
  },
  body: {
    flex: 1,
    minWidth: 0,
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  message: {
    color: '#78350f',
  },
});

type Props = {
  drift: SerializedDrift | null;
};

export type SerializedDrift = Omit<Drift, 'prevFinishedAt' | 'currFinishedAt'> & {
  prevFinishedAt: string | null;
  currFinishedAt: string | null;
};

export function DriftBanner({ drift }: Props) {
  const s = useStyles();
  const [dismissed, setDismissed] = useState(false);
  if (!drift || dismissed) return null;

  const pct = Math.abs(drift.pct * 100).toFixed(0);
  const lost = Math.abs(drift.delta).toLocaleString();

  return (
    <div className={s.banner} role="alert">
      <Warning24Filled className={s.icon} />
      <div className={s.body}>
        <Body1 className={s.message}>
          <strong>Standings dropped {lost} rows ({pct}%)</strong> vs the previous successful
          scrape ({drift.prevCount.toLocaleString()} → {drift.currCount.toLocaleString()}).
          An upstream source may have changed its URL pattern or HTML structure — check{' '}
          <code>scrape_log.txt</code> before trusting this view.
        </Body1>
      </div>
      <Button
        appearance="transparent"
        size="small"
        icon={<Dismiss20Regular />}
        aria-label="Dismiss"
        onClick={() => setDismissed(true)}
      />
    </div>
  );
}
