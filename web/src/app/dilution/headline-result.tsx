'use client';

import {
  Body1,
  Caption1,
  Title2,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import {
  ArrowDownFilled,
  ArrowUpFilled,
} from '@fluentui/react-icons';
import {
  COHORT_CATEGORIES,
  COHORT_COLORS,
  COHORT_SHORT,
  type CohortStat,
  type DilutionMetricLabel,
} from '@/lib/analytics/dilution';

const useStyles = makeStyles({
  wrap: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacingVerticalM,
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))',
    gap: tokens.spacingHorizontalM,
  },
  card: {
    position: 'relative',
    backgroundColor: tokens.colorNeutralBackground1,
    borderRadius: tokens.borderRadiusXLarge,
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    boxShadow: tokens.shadow4,
    padding: `${tokens.spacingVerticalL} ${tokens.spacingHorizontalL}`,
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacingVerticalXS,
    overflow: 'hidden',
  },
  stripe: {
    position: 'absolute',
    left: 0,
    top: 0,
    bottom: 0,
    width: '4px',
  },
  label: {
    color: tokens.colorNeutralForeground3,
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
    fontSize: '11px',
  },
  value: {
    fontVariantNumeric: 'tabular-nums',
    lineHeight: 1.1,
  },
  metaRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: tokens.spacingHorizontalXS,
    color: tokens.colorNeutralForeground3,
  },
  delta: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '2px',
    fontVariantNumeric: 'tabular-nums',
    fontWeight: tokens.fontWeightSemibold,
    padding: `2px ${tokens.spacingHorizontalXS}`,
    borderRadius: tokens.borderRadiusMedium,
  },
  deltaBad: {
    color: '#b91c1c',
    backgroundColor: '#fee2e2',
  },
  deltaGood: {
    color: '#15803d',
    backgroundColor: '#dcfce7',
  },
  caption: {
    color: tokens.colorNeutralForeground2,
  },
});

const RATE_METRICS: ReadonlySet<DilutionMetricLabel> = new Set([
  'Points %',
  'Win %',
]);

function isRateMetric(metric: DilutionMetricLabel): boolean {
  return RATE_METRICS.has(metric);
}

function formatValue(v: number | null, metric: DilutionMetricLabel): string {
  if (v === null) return '—';
  if (isRateMetric(metric)) return `${(v * 100).toFixed(1)}%`;
  return v.toFixed(3);
}

/** Format the absolute delta chip — percentage points for rate metrics,
 *  raw decimal for Goal Diff/Game. */
function formatDeltaChip(delta: number, metric: DilutionMetricLabel): string {
  const abs = Math.abs(delta);
  if (isRateMetric(metric)) return `${(abs * 100).toFixed(1)}pp`;
  return abs.toFixed(2);
}

type Props = {
  cohortStats: CohortStat[];
  diluted: {
    mean: number;
    count: number;
    deltaVsNeighbours: number | null;
    neighbourMean: number | null;
  };
  metricLabel: DilutionMetricLabel;
};

export function HeadlineResult({ cohortStats, diluted, metricLabel }: Props) {
  const s = useStyles();
  const dilutedCategory = 'Just Above Threshold (Diluted)' as const;

  // Relative % difference is well-defined when the neighbour mean is positive
  // and we have a delta. For Goal Diff/Game with near-zero or negative neighbour
  // averages, relative % is misleading — we fall back to the absolute statement.
  const canShowRelative =
    diluted.deltaVsNeighbours !== null &&
    diluted.neighbourMean !== null &&
    diluted.neighbourMean > 0.01 &&
    isRateMetric(metricLabel);

  const relativePct = canShowRelative
    ? (diluted.mean / (diluted.neighbourMean as number)) - 1
    : null;

  return (
    <div className={s.wrap}>
      <div className={s.grid}>
        {COHORT_CATEGORIES.map((cat) => {
          const stat = cohortStats.find((c) => c.category === cat);
          const isDiluted = cat === dilutedCategory;
          const showDelta = isDiluted && diluted.deltaVsNeighbours !== null;
          const deltaNegative = (diluted.deltaVsNeighbours ?? 0) < 0;
          return (
            <div key={cat} className={s.card}>
              <span
                className={s.stripe}
                style={{ backgroundColor: COHORT_COLORS[cat] }}
                aria-hidden
              />
              <Caption1 className={s.label}>{COHORT_SHORT[cat]}</Caption1>
              <Title2 as="span" block className={s.value}>
                {formatValue(stat?.mean ?? null, metricLabel)}
              </Title2>
              <div className={s.metaRow}>
                <Caption1>n = {stat?.count ?? 0}</Caption1>
                {showDelta && (
                  <span
                    className={`${s.delta} ${deltaNegative ? s.deltaBad : s.deltaGood}`}
                    title={`Diluted mean − avg(Below + Large): ${diluted.deltaVsNeighbours!.toFixed(3)}`}
                  >
                    {deltaNegative ? <ArrowDownFilled /> : <ArrowUpFilled />}
                    {formatDeltaChip(diluted.deltaVsNeighbours!, metricLabel)}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
      {diluted.count >= 3 && relativePct !== null && (
        <Body1 className={s.caption}>
          Diluted communities perform{' '}
          <strong>
            {Math.abs(relativePct * 100).toFixed(0)}%{' '}
            {relativePct < 0 ? 'worse' : 'better'}
          </strong>{' '}
          than the average of their neighbouring cohorts ({metricLabel}, n={diluted.count}{' '}
          community-season-age observations).
        </Body1>
      )}
      {diluted.count >= 3 &&
        relativePct === null &&
        diluted.deltaVsNeighbours !== null && (
          <Body1 className={s.caption}>
            Diluted communities score{' '}
            <strong>
              {Math.abs(diluted.deltaVsNeighbours).toFixed(2)}{' '}
              {diluted.deltaVsNeighbours < 0 ? 'fewer' : 'more'}
            </strong>{' '}
            {metricLabel.toLowerCase()} than the average of their neighbouring cohorts (n=
            {diluted.count} community-season-age observations).
          </Body1>
        )}
      {diluted.count < 3 && diluted.count > 0 && (
        <Body1 className={s.caption}>
          Only {diluted.count} observation{diluted.count === 1 ? '' : 's'} in the Diluted
          cohort — widen Season/Age filters for a meaningful comparison.
        </Body1>
      )}
    </div>
  );
}
