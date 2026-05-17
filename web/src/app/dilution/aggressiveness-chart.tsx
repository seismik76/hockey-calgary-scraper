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
import { ArrowTrendingLines24Regular } from '@fluentui/react-icons';
import { SectionCard } from '@/app/analytics/section-card';
import { communityColor } from '@/lib/analytics/communities';
import type {
  AggressivenessPoint,
  DilutionMetricLabel,
} from '@/lib/analytics/dilution';

type TooltipPayload = { payload: AggressivenessPoint };

function TrendTooltip(props: { active?: boolean; payload?: TooltipPayload[] }) {
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
        minWidth: '200px',
      }}
    >
      <div style={{ fontWeight: tokens.fontWeightSemibold }}>
        {d.community} ({d.season})
      </div>
      <div style={{ color: tokens.colorNeutralForeground1, marginTop: 4 }}>
        Aggressiveness: <strong>{(d.aggressiveness * 100).toFixed(1)}%</strong>
      </div>
      <div style={{ color: tokens.colorNeutralForeground1 }}>
        Performance: <strong>{d.performance.toFixed(3)}</strong>
      </div>
      <div style={{ color: tokens.colorNeutralForeground2, marginTop: 4 }}>
        Teams: {d.totalTeams} · Tier 1: {d.tier1Count}
      </div>
    </div>
  );
}

export function AggressivenessChart({
  series,
  metricLabel,
}: {
  series: { community: string; points: AggressivenessPoint[] }[];
  metricLabel: DilutionMetricLabel;
}) {
  const nonEmpty = series.filter((s) => s.points.length > 0);

  return (
    <SectionCard
      icon={<ArrowTrendingLines24Regular />}
      title="Tiering aggressiveness vs. performance"
      description={
        <>
          Trails connect a community across seasons.{' '}
          <strong>Down &amp; right</strong> = became more aggressive, performance dropped.{' '}
          <strong>Up &amp; right</strong> = aggressive and still healthy.
        </>
      }
    >
      {nonEmpty.length === 0 ? (
        <div style={{ color: tokens.colorNeutralForeground2 }}>No data.</div>
      ) : (
        <div style={{ width: '100%', height: 460 }}>
          <ResponsiveContainer>
            <ScatterChart margin={{ top: 12, right: 30, left: 0, bottom: 28 }}>
              <CartesianGrid
                strokeDasharray="2 4"
                stroke={tokens.colorNeutralStroke3}
              />
              <XAxis
                type="number"
                dataKey="aggressiveness"
                domain={[0, 'auto']}
                tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
                tick={{ fontSize: 12, fill: tokens.colorNeutralForeground2 }}
                tickLine={false}
                axisLine={{ stroke: tokens.colorNeutralStroke2 }}
                label={{
                  value: 'Tiering aggressiveness (% Tier 1)',
                  position: 'insideBottom',
                  offset: -16,
                  style: {
                    textAnchor: 'middle',
                    fill: tokens.colorNeutralForeground3,
                    fontSize: 12,
                  },
                }}
              />
              <YAxis
                type="number"
                dataKey="performance"
                tick={{ fontSize: 12, fill: tokens.colorNeutralForeground2 }}
                tickLine={false}
                axisLine={false}
                width={56}
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
              <Tooltip cursor={false} content={<TrendTooltip />} />
              {nonEmpty.map((s, i) => (
                <Scatter
                  key={s.community}
                  name={s.community}
                  data={s.points}
                  fill={communityColor(s.community, i)}
                  line={{ stroke: communityColor(s.community, i), strokeWidth: 1.5 }}
                  lineType="joint"
                  shape="circle"
                  isAnimationActive={false}
                />
              ))}
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      )}
    </SectionCard>
  );
}
