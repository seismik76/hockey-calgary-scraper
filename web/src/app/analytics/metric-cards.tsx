'use client';

import { Caption1, Title2, makeStyles, tokens } from '@fluentui/react-components';
import {
  People24Regular,
  Trophy24Regular,
  CalendarLtr24Regular,
  Home24Regular,
} from '@fluentui/react-icons';
import { type ReactNode } from 'react';

const ACCENTS: Record<string, { bg: string; fg: string; stripe: string; icon: ReactNode }> = {
  Teams: {
    bg: '#dbeafe',
    fg: '#1d4ed8',
    stripe: '#3b82f6',
    icon: <People24Regular />,
  },
  Leagues: {
    bg: '#fef3c7',
    fg: '#b45309',
    stripe: '#f59e0b',
    icon: <Trophy24Regular />,
  },
  Seasons: {
    bg: '#d1fae5',
    fg: '#047857',
    stripe: '#10b981',
    icon: <CalendarLtr24Regular />,
  },
  Communities: {
    bg: '#ede9fe',
    fg: '#6d28d9',
    stripe: '#8b5cf6',
    icon: <Home24Regular />,
  },
};

const useStyles = makeStyles({
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap: tokens.spacingHorizontalL,
  },
  card: {
    position: 'relative',
    backgroundColor: tokens.colorNeutralBackground1,
    borderRadius: tokens.borderRadiusXLarge,
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    boxShadow: tokens.shadow4,
    padding: tokens.spacingHorizontalXL,
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacingHorizontalM,
    overflow: 'hidden',
  },
  stripe: {
    position: 'absolute',
    left: 0,
    top: 0,
    bottom: 0,
    width: '4px',
  },
  iconBox: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '44px',
    height: '44px',
    flexShrink: 0,
    borderRadius: tokens.borderRadiusLarge,
  },
  text: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacingVerticalXXS,
    minWidth: 0,
  },
  value: {
    lineHeight: 1.1,
    fontVariantNumeric: 'tabular-nums',
  },
  label: {
    color: tokens.colorNeutralForeground3,
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
    fontSize: '11px',
  },
});

type Stat = { label: string; value: number };

export function MetricCards({ stats }: { stats: Stat[] }) {
  const s = useStyles();
  return (
    <div className={s.grid}>
      {stats.map((stat) => {
        const accent = ACCENTS[stat.label] ?? {
          bg: tokens.colorBrandBackground2,
          fg: tokens.colorBrandForeground1,
          stripe: tokens.colorBrandStroke1,
          icon: <Trophy24Regular />,
        };
        return (
          <div key={stat.label} className={s.card}>
            <span className={s.stripe} style={{ backgroundColor: accent.stripe }} aria-hidden />
            <span
              className={s.iconBox}
              style={{ backgroundColor: accent.bg, color: accent.fg }}
              aria-hidden
            >
              {accent.icon}
            </span>
            <div className={s.text}>
              <Caption1 className={s.label}>{stat.label}</Caption1>
              <Title2 as="span" block className={s.value}>
                {stat.value.toLocaleString()}
              </Title2>
            </div>
          </div>
        );
      })}
    </div>
  );
}
