'use client';

import { useState } from 'react';
import {
  Body1,
  Button,
  Link,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import { Table24Regular } from '@fluentui/react-icons';
import { SectionCard } from './section-card';
import type { StandingRow } from '@/lib/analytics/data';

const PAGE_SIZE = 50;

const COLUMNS: {
  key: keyof StandingRow;
  header: string;
  align?: 'right';
  format?: (v: unknown) => string;
}[] = [
  { key: 'teamLabel', header: 'Team' },
  { key: 'community', header: 'Community' },
  { key: 'season', header: 'Season' },
  { key: 'ageCategory', header: 'Age' },
  { key: 'tier', header: 'Tier' },
  { key: 'type', header: 'Type' },
  { key: 'gp', header: 'GP', align: 'right' },
  { key: 'w', header: 'W', align: 'right' },
  { key: 'l', header: 'L', align: 'right' },
  { key: 't', header: 'T', align: 'right' },
  { key: 'pts', header: 'PTS', align: 'right' },
  { key: 'gf', header: 'GF', align: 'right' },
  { key: 'ga', header: 'GA', align: 'right' },
  { key: 'diff', header: 'Diff', align: 'right' },
  {
    key: 'winPct',
    header: 'Win %',
    align: 'right',
    format: (v) => (typeof v === 'number' ? `${(v * 100).toFixed(1)}%` : ''),
  },
  {
    key: 'pointsPct',
    header: 'Pts %',
    align: 'right',
    format: (v) => (typeof v === 'number' ? `${(v * 100).toFixed(1)}%` : ''),
  },
  {
    key: 'goalDiffPerGame',
    header: 'Diff/GP',
    align: 'right',
    format: (v) => (typeof v === 'number' ? v.toFixed(2) : ''),
  },
];

const useStyles = makeStyles({
  scroller: {
    overflowX: 'auto',
    borderRadius: tokens.borderRadiusLarge,
    border: `1px solid ${tokens.colorNeutralStroke2}`,
  },
  table: {
    width: '100%',
    borderCollapse: 'separate',
    borderSpacing: 0,
    fontSize: '13px',
  },
  th: {
    textAlign: 'left',
    fontWeight: tokens.fontWeightSemibold,
    fontSize: '11px',
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
    color: tokens.colorNeutralForeground3,
    padding: `${tokens.spacingVerticalS} ${tokens.spacingHorizontalM}`,
    backgroundColor: tokens.colorNeutralBackground2,
    borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
    whiteSpace: 'nowrap',
    position: 'sticky',
    top: 0,
  },
  thRight: { textAlign: 'right' },
  td: {
    padding: `${tokens.spacingVerticalM} ${tokens.spacingHorizontalM}`,
    borderBottom: `1px solid ${tokens.colorNeutralStroke3}`,
    whiteSpace: 'nowrap',
    color: tokens.colorNeutralForeground1,
  },
  tdRight: {
    textAlign: 'right',
    fontVariantNumeric: 'tabular-nums',
  },
  row: {
    ':hover': { backgroundColor: tokens.colorNeutralBackground2 },
  },
  footer: {
    display: 'flex',
    justifyContent: 'center',
    paddingTop: tokens.spacingVerticalM,
  },
});

export function DetailTable({ rows }: { rows: StandingRow[] }) {
  const [shown, setShown] = useState(PAGE_SIZE);
  const s = useStyles();
  const visible = rows.slice(0, shown);

  return (
    <SectionCard
      icon={<Table24Regular />}
      title="Detailed data"
      description={
        <Body1 style={{ color: tokens.colorNeutralForeground2 }}>
          {rows.length.toLocaleString()} team-season rows match the current filters.
        </Body1>
      }
    >
      <div className={s.scroller}>
        <table className={s.table}>
          <thead>
            <tr>
              {COLUMNS.map((c) => (
                <th
                  key={String(c.key)}
                  className={`${s.th} ${c.align === 'right' ? s.thRight : ''}`}
                >
                  {c.header}
                </th>
              ))}
              <th className={s.th}>Source</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((r, i) => (
              <tr key={`${r.team}-${r.season}-${r.league}-${i}`} className={s.row}>
                {COLUMNS.map((c) => {
                  const raw = r[c.key];
                  const display = c.format ? c.format(raw) : (raw ?? '');
                  return (
                    <td
                      key={String(c.key)}
                      className={`${s.td} ${c.align === 'right' ? s.tdRight : ''}`}
                    >
                      {String(display)}
                    </td>
                  );
                })}
                <td className={s.td}>
                  {r.source ? (
                    <Link href={r.source} target="_blank" rel="noopener noreferrer">
                      open
                    </Link>
                  ) : (
                    ''
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {shown < rows.length && (
        <div className={s.footer}>
          <Button appearance="subtle" onClick={() => setShown((n) => n + PAGE_SIZE)}>
            Show {Math.min(PAGE_SIZE, rows.length - shown)} more
          </Button>
        </div>
      )}
    </SectionCard>
  );
}
