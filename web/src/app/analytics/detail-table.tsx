'use client';

import { useMemo, useState } from 'react';
import {
  Body1,
  Button,
  Caption1,
  Input,
  Link,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import {
  ArrowDown16Regular,
  ArrowSort16Regular,
  ArrowUp16Regular,
  DismissCircle20Regular,
  Search20Regular,
  Table24Regular,
} from '@fluentui/react-icons';
import { SectionCard } from './section-card';
import type { StandingRow } from '@/lib/analytics/data';

const PAGE_SIZE = 50;

type Column = {
  key: keyof StandingRow;
  header: string;
  align?: 'right';
  format?: (v: unknown) => string;
};

const COLUMNS: Column[] = [
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

// Columns searched against by the free-text query. The team label is
// already-composed (community + age + tier + #), so it covers most queries on
// its own, but we add the raw fields for users who paste in upstream names.
const SEARCH_KEYS: (keyof StandingRow)[] = [
  'teamLabel',
  'team',
  'community',
  'league',
  'season',
];

const useStyles = makeStyles({
  controls: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacingHorizontalM,
    flexWrap: 'wrap',
  },
  search: {
    flex: '1 1 280px',
    maxWidth: '420px',
  },
  count: {
    color: tokens.colorNeutralForeground2,
    fontVariantNumeric: 'tabular-nums',
  },
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
    padding: 0,
    backgroundColor: tokens.colorNeutralBackground2,
    borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
    whiteSpace: 'nowrap',
    position: 'sticky',
    top: 0,
  },
  // Header cells become a clickable button so the sort affordance is obvious.
  thButton: {
    width: '100%',
    background: 'transparent',
    border: 'none',
    padding: `${tokens.spacingVerticalS} ${tokens.spacingHorizontalM}`,
    cursor: 'pointer',
    color: 'inherit',
    font: 'inherit',
    textAlign: 'left',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    whiteSpace: 'nowrap',
    ':hover': {
      backgroundColor: tokens.colorNeutralBackground2Hover,
      color: tokens.colorNeutralForeground1,
    },
  },
  thButtonActive: {
    color: tokens.colorBrandForeground1,
  },
  thButtonRight: {
    justifyContent: 'flex-end',
    textAlign: 'right',
  },
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
  empty: {
    padding: tokens.spacingVerticalXXL,
    textAlign: 'center',
    color: tokens.colorNeutralForeground3,
  },
});

type SortState = { key: keyof StandingRow; dir: 'asc' | 'desc' } | null;

function compareValues(a: unknown, b: unknown): number {
  // null/undefined sort to the end regardless of direction.
  if (a == null && b == null) return 0;
  if (a == null) return 1;
  if (b == null) return -1;
  if (typeof a === 'number' && typeof b === 'number') return a - b;
  return String(a).localeCompare(String(b));
}

export function DetailTable({ rows }: { rows: StandingRow[] }) {
  const s = useStyles();
  const [shown, setShown] = useState(PAGE_SIZE);
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState<SortState>(null);

  const processed = useMemo(() => {
    const q = query.trim().toLowerCase();
    let out = rows;
    if (q) {
      out = out.filter((r) =>
        SEARCH_KEYS.some((k) => {
          const v = r[k];
          return typeof v === 'string' && v.toLowerCase().includes(q);
        }),
      );
    }
    if (sort) {
      out = [...out].sort((a, b) => {
        const cmp = compareValues(a[sort.key], b[sort.key]);
        return sort.dir === 'asc' ? cmp : -cmp;
      });
    }
    return out;
  }, [rows, query, sort]);

  const visible = processed.slice(0, shown);

  function toggleSort(key: keyof StandingRow) {
    setSort((prev) => {
      if (!prev || prev.key !== key) return { key, dir: 'desc' };
      if (prev.dir === 'desc') return { key, dir: 'asc' };
      return null; // third click clears the sort
    });
    setShown(PAGE_SIZE);
  }

  function sortIcon(key: keyof StandingRow) {
    if (!sort || sort.key !== key) return <ArrowSort16Regular />;
    return sort.dir === 'desc' ? <ArrowDown16Regular /> : <ArrowUp16Regular />;
  }

  return (
    <SectionCard
      icon={<Table24Regular />}
      title="Detailed data"
      description={
        <Body1 style={{ color: tokens.colorNeutralForeground2 }}>
          {processed.length.toLocaleString()} of {rows.length.toLocaleString()} team-season
          rows match the current filters
          {query ? ' and search' : ''}.
        </Body1>
      }
    >
      <div className={s.controls}>
        <div className={s.search}>
          <Input
            placeholder="Search team, community, league…"
            value={query}
            contentBefore={<Search20Regular />}
            contentAfter={
              query ? (
                <Button
                  appearance="transparent"
                  size="small"
                  icon={<DismissCircle20Regular />}
                  onClick={() => setQuery('')}
                  aria-label="Clear search"
                />
              ) : undefined
            }
            onChange={(_, data) => {
              setQuery(data.value);
              setShown(PAGE_SIZE);
            }}
          />
        </div>
        {sort && (
          <Caption1 className={s.count}>
            Sorted by <strong>{COLUMNS.find((c) => c.key === sort.key)?.header}</strong>{' '}
            ({sort.dir === 'desc' ? 'high → low' : 'low → high'})
          </Caption1>
        )}
      </div>

      {processed.length === 0 ? (
        <div className={s.empty}>
          <Body1>No rows match the current search.</Body1>
        </div>
      ) : (
        <div className={s.scroller}>
          <table className={s.table}>
            <thead>
              <tr>
                {COLUMNS.map((c) => {
                  const isActive = sort?.key === c.key;
                  return (
                    <th key={String(c.key)} className={s.th}>
                      <button
                        type="button"
                        onClick={() => toggleSort(c.key)}
                        className={`${s.thButton} ${
                          c.align === 'right' ? s.thButtonRight : ''
                        } ${isActive ? s.thButtonActive : ''}`}
                      >
                        {c.header}
                        {sortIcon(c.key)}
                      </button>
                    </th>
                  );
                })}
                <th className={s.th}>
                  <span style={{ padding: `${tokens.spacingVerticalS} ${tokens.spacingHorizontalM}`, display: 'inline-block' }}>
                    Source
                  </span>
                </th>
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
      )}
      {shown < processed.length && (
        <div className={s.footer}>
          <Button appearance="subtle" onClick={() => setShown((n) => n + PAGE_SIZE)}>
            Show {Math.min(PAGE_SIZE, processed.length - shown)} more
          </Button>
        </div>
      )}
    </SectionCard>
  );
}
