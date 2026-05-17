import type { StandingRow } from './data';

export const METRICS = {
  Points: 'pts',
  Wins: 'w',
  Losses: 'l',
  'Goal Diff': 'diff',
  'Goals For': 'gf',
  'Goals Against': 'ga',
} as const;

export type MetricLabel = keyof typeof METRICS;
export type MetricKey = (typeof METRICS)[MetricLabel];

export const METRIC_LABELS: MetricLabel[] = Object.keys(METRICS) as MetricLabel[];

export function metricValue(row: StandingRow, key: MetricKey): number {
  const v = row[key];
  return typeof v === 'number' ? v : 0;
}
