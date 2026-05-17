'use client';

import { useMemo } from 'react';
import {
  Body1,
  Button,
  Caption1,
  Popover,
  PopoverSurface,
  PopoverTrigger,
  Tooltip,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import { Info20Regular } from '@fluentui/react-icons';
import type { StandingRow } from '@/lib/analytics/data';

const useStyles = makeStyles({
  surface: {
    padding: tokens.spacingHorizontalM,
    minWidth: '420px',
    maxWidth: '560px',
  },
  summary: {
    marginBottom: tokens.spacingVerticalM,
    color: tokens.colorNeutralForeground2,
  },
  matrix: {
    display: 'grid',
    gap: '2px',
    fontSize: '12px',
  },
  th: {
    padding: '4px 8px',
    fontWeight: tokens.fontWeightSemibold,
    color: tokens.colorNeutralForeground3,
    textTransform: 'uppercase',
    fontSize: '10px',
    letterSpacing: '0.04em',
    textAlign: 'center',
  },
  rowLabel: {
    padding: '4px 8px',
    fontWeight: tokens.fontWeightSemibold,
    color: tokens.colorNeutralForeground1,
    whiteSpace: 'nowrap',
  },
  cell: {
    padding: '4px 8px',
    textAlign: 'center',
    fontVariantNumeric: 'tabular-nums',
    borderRadius: '4px',
    color: tokens.colorNeutralForeground1,
  },
  footnote: {
    marginTop: tokens.spacingVerticalS,
    color: tokens.colorNeutralForeground3,
  },
});

type Cell = {
  season: string;
  age: string;
  count: number;
};

function buildMatrix(rows: StandingRow[]): {
  seasons: string[];
  ages: string[];
  cells: Map<string, number>;
  max: number;
} {
  const seasonSet = new Set<string>();
  const ageSet = new Set<string>();
  const cells = new Map<string, number>();

  for (const r of rows) {
    seasonSet.add(r.season);
    ageSet.add(r.ageCategory);
    const k = `${r.season}|${r.ageCategory}`;
    cells.set(k, (cells.get(k) ?? 0) + 1);
  }

  const seasons = Array.from(seasonSet).sort().reverse();
  const ages = Array.from(ageSet).sort((a, b) => {
    // Sort U7, U9, U11, ... numerically; Other last
    const an = parseInt(a.replace(/\D/g, ''), 10);
    const bn = parseInt(b.replace(/\D/g, ''), 10);
    if (Number.isNaN(an) && Number.isNaN(bn)) return a.localeCompare(b);
    if (Number.isNaN(an)) return 1;
    if (Number.isNaN(bn)) return -1;
    return an - bn;
  });
  const max = Math.max(0, ...cells.values());
  return { seasons, ages, cells, max };
}

function cellColor(value: number, max: number): string {
  if (value === 0 || max === 0) return tokens.colorNeutralBackground3;
  const alpha = 0.15 + (value / max) * 0.55;
  return `rgba(34, 197, 94, ${alpha.toFixed(2)})`;
}

export function CoveragePopover({ rows }: { rows: StandingRow[] }) {
  const s = useStyles();
  const matrix = useMemo(() => buildMatrix(rows), [rows]);

  const communityCount = useMemo(
    () => new Set(rows.map((r) => r.community).filter(Boolean)).size,
    [rows],
  );

  const gridTemplateColumns = `auto repeat(${matrix.ages.length}, minmax(48px, 1fr))`;

  return (
    <Popover>
      <PopoverTrigger disableButtonEnhancement>
        <Tooltip content="About this data" relationship="label">
          <Button
            appearance="subtle"
            size="small"
            icon={<Info20Regular />}
            aria-label="About this data"
          />
        </Tooltip>
      </PopoverTrigger>
      <PopoverSurface className={s.surface}>
        <Body1 className={s.summary}>
          <strong>{rows.length.toLocaleString()}</strong> team-season records across{' '}
          <strong>{matrix.seasons.length}</strong> seasons and{' '}
          <strong>{communityCount}</strong> communities.
        </Body1>
        <div className={s.matrix} style={{ gridTemplateColumns }}>
          <div />
          {matrix.ages.map((age) => (
            <div key={age} className={s.th}>
              {age}
            </div>
          ))}
          {matrix.seasons.map((season) => (
            <div
              key={season}
              style={{ display: 'contents' }}
              role="row"
            >
              <div className={s.rowLabel}>{season}</div>
              {matrix.ages.map((age) => {
                const v = matrix.cells.get(`${season}|${age}`) ?? 0;
                return (
                  <div
                    key={age}
                    className={s.cell}
                    style={{ backgroundColor: cellColor(v, matrix.max) }}
                    title={`${season} · ${age}: ${v} rows`}
                  >
                    {v === 0 ? '—' : v.toLocaleString()}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
        <Caption1 className={s.footnote}>
          Cell shading scales with row count — darker green = more standings recorded.
        </Caption1>
      </PopoverSurface>
    </Popover>
  );
}
