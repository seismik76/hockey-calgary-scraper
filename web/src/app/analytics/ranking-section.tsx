'use client';

import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts';
import { tokens } from '@fluentui/react-components';
import { Trophy24Regular } from '@fluentui/react-icons';
import { metricValue, type MetricKey, type MetricLabel } from '@/lib/analytics/metrics';
import type { StandingRow } from '@/lib/analytics/data';
import { rdYlGn, scaleValue } from '@/lib/analytics/color-scale';
import { SectionCard } from './section-card';

type Props = {
  rows: StandingRow[];
  metricLabel: MetricLabel;
  metricKey: MetricKey;
};

function buildRanking(rows: StandingRow[], metricKey: MetricKey) {
  const sums = new Map<string, { sum: number; count: number }>();
  for (const r of rows) {
    if (!r.community) continue;
    const v = metricValue(r, metricKey);
    const e = sums.get(r.community);
    if (e) {
      e.sum += v;
      e.count += 1;
    } else {
      sums.set(r.community, { sum: v, count: 1 });
    }
  }
  return Array.from(sums.entries())
    .map(([community, { sum, count }]) => ({ community, value: count > 0 ? sum / count : 0 }))
    .sort((a, b) => b.value - a.value);
}

export function RankingSection({ rows, metricLabel, metricKey }: Props) {
  const ranking = buildRanking(rows, metricKey);
  const min = ranking.length ? ranking[ranking.length - 1].value : 0;
  const max = ranking.length ? ranking[0].value : 0;

  return (
    <SectionCard
      icon={<Trophy24Regular />}
      title="Strongest vs. weakest"
      description={
        <>
          Communities ranked by average <strong>{metricLabel}</strong> over the selected period.
        </>
      }
    >
      <div style={{ width: '100%', height: 420 }}>
        <ResponsiveContainer>
          <BarChart data={ranking} margin={{ top: 12, right: 16, left: 0, bottom: 60 }}>
            <CartesianGrid
              strokeDasharray="2 4"
              stroke={tokens.colorNeutralStroke3}
              vertical={false}
            />
            <XAxis
              dataKey="community"
              tick={{ fontSize: 12, fill: tokens.colorNeutralForeground2 }}
              tickLine={false}
              axisLine={{ stroke: tokens.colorNeutralStroke2 }}
              angle={-30}
              textAnchor="end"
              interval={0}
              height={70}
            />
            <YAxis
              tick={{ fontSize: 12, fill: tokens.colorNeutralForeground2 }}
              tickLine={false}
              axisLine={false}
              width={48}
            />
            <Tooltip
              cursor={{ fill: tokens.colorNeutralBackground3 }}
              contentStyle={{
                backgroundColor: tokens.colorNeutralBackground1,
                border: `1px solid ${tokens.colorNeutralStroke2}`,
                borderRadius: tokens.borderRadiusMedium,
                boxShadow: tokens.shadow8,
                fontSize: '12px',
              }}
              formatter={(v) => (typeof v === 'number' ? v.toFixed(3) : String(v))}
            />
            <Bar dataKey="value" radius={[6, 6, 0, 0]}>
              {ranking.map((r) => (
                <Cell key={r.community} fill={rdYlGn(scaleValue(r.value, min, max))} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}
