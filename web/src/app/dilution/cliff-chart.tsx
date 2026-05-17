'use client';

import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { tokens } from '@fluentui/react-components';
import { ChartMultiple24Regular } from '@fluentui/react-icons';
import { SectionCard } from '@/app/analytics/section-card';
import {
  COHORT_CATEGORIES,
  COHORT_COLORS,
  COHORT_SHORT,
  type Category,
  type CohortStat,
  type CommunityStat,
} from '@/lib/analytics/dilution';
import type { DilutionMetricLabel } from '@/lib/analytics/dilution';

// Cheap deterministic hash → [-0.25, 0.25] so jitter stays the same across renders.
function jitter(seed: string): number {
  let h = 0;
  for (let i = 0; i < seed.length; i++) {
    h = (h * 31 + seed.charCodeAt(i)) | 0;
  }
  const t = ((h % 1000) + 1000) % 1000;
  return (t / 1000 - 0.5) * 0.5;
}

type Point = {
  x: number;
  y: number;
  category: Category;
  community: string;
  season: string;
  ageCategory: string;
  totalTeams: number;
  tier1Count: number;
};

type MeanPoint = { x: number; y: number; category: Category };

function MeanShape(props: { cx?: number; cy?: number; payload?: MeanPoint }) {
  const { cx, cy, payload } = props;
  if (cx === undefined || cy === undefined || !payload) return null;
  return (
    <line
      x1={cx - 28}
      x2={cx + 28}
      y1={cy}
      y2={cy}
      stroke={COHORT_COLORS[payload.category as Exclude<Category, 'Other'>]}
      strokeWidth={4}
      strokeLinecap="round"
    />
  );
}

type TooltipPayload = { payload: Point };

function CliffTooltip(props: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!props.active || !props.payload || props.payload.length === 0) return null;
  const d = props.payload[0].payload;
  return (
    <div
      style={{
        backgroundColor: tokens.colorNeutralBackground1,
        border: `1px solid ${tokens.colorNeutralStroke2}`,
        borderRadius: tokens.borderRadiusMedium,
        boxShadow: tokens.shadow8,
        fontSize: '12px',
        padding: tokens.spacingHorizontalM,
        minWidth: '180px',
      }}
    >
      <div style={{ fontWeight: tokens.fontWeightSemibold }}>
        {d.community} ({d.season})
      </div>
      <div style={{ color: tokens.colorNeutralForeground2 }}>{d.ageCategory}</div>
      <div style={{ marginTop: 6, color: tokens.colorNeutralForeground1 }}>
        Performance: <strong>{d.y.toFixed(3)}</strong>
      </div>
      <div style={{ color: tokens.colorNeutralForeground2 }}>
        Teams: {d.totalTeams} · Tier 1: {d.tier1Count}
      </div>
    </div>
  );
}

export function CliffChart({
  communityStats,
  cohortStats,
  metricLabel,
}: {
  communityStats: CommunityStat[];
  cohortStats: CohortStat[];
  metricLabel: DilutionMetricLabel;
}) {
  const series = COHORT_CATEGORIES.map((category) => ({
    category,
    color: COHORT_COLORS[category],
    points: communityStats
      .filter((s) => s.category === category)
      .map((s, i): Point => {
        const x = COHORT_CATEGORIES.indexOf(category);
        return {
          x: x + jitter(`${s.community}|${s.season}|${s.ageCategory}|${i}`),
          y: s.overallPerformance,
          category,
          community: s.community,
          season: s.season,
          ageCategory: s.ageCategory,
          totalTeams: s.totalTeams,
          tier1Count: s.tier1Count,
        };
      }),
  }));

  const meanPoints: MeanPoint[] = cohortStats
    .filter((c) => c.mean !== null)
    .map((c) => ({
      x: COHORT_CATEGORIES.indexOf(c.category),
      y: c.mean as number,
      category: c.category,
    }));

  const hasAnyPoint = series.some((s) => s.points.length > 0);

  return (
    <SectionCard
      icon={<ChartMultiple24Regular />}
      title="The dilution cliff"
      description={
        <>
          Each dot is one community-season-age. Thick bars are cohort means. The hypothesis:{' '}
          <strong>red (Diluted)</strong> sits below its green/blue neighbours.
        </>
      }
    >
      {!hasAnyPoint ? (
        <div style={{ color: tokens.colorNeutralForeground2 }}>
          No data in the selected cohorts.
        </div>
      ) : (
        <div style={{ width: '100%', height: 420 }}>
          <ResponsiveContainer>
            <ScatterChart margin={{ top: 12, right: 20, left: 0, bottom: 10 }}>
              <CartesianGrid
                strokeDasharray="2 4"
                stroke={tokens.colorNeutralStroke3}
                vertical={false}
              />
              <XAxis
                type="number"
                dataKey="x"
                domain={[-0.5, 3.5]}
                ticks={[0, 1, 2, 3]}
                tickFormatter={(v: number) =>
                  COHORT_SHORT[COHORT_CATEGORIES[v]] ?? ''
                }
                tick={{ fontSize: 12, fill: tokens.colorNeutralForeground2 }}
                tickLine={false}
                axisLine={{ stroke: tokens.colorNeutralStroke2 }}
                allowDataOverflow
                interval={0}
              />
              <YAxis
                type="number"
                dataKey="y"
                tick={{ fontSize: 12, fill: tokens.colorNeutralForeground2 }}
                tickLine={false}
                axisLine={false}
                width={48}
                label={{
                  value: metricLabel,
                  angle: -90,
                  position: 'insideLeft',
                  style: {
                    textAnchor: 'middle',
                    fill: tokens.colorNeutralForeground3,
                    fontSize: 12,
                  },
                }}
              />
              <Tooltip
                cursor={{ stroke: tokens.colorNeutralStroke3, strokeDasharray: '3 3' }}
                content={<CliffTooltip />}
              />
              {series.map((s) => (
                <Scatter
                  key={s.category}
                  name={s.category}
                  data={s.points}
                  fill={s.color}
                  opacity={0.75}
                  isAnimationActive={false}
                />
              ))}
              <Scatter
                name="Mean"
                data={meanPoints}
                shape={<MeanShape />}
                isAnimationActive={false}
              />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      )}
    </SectionCard>
  );
}
