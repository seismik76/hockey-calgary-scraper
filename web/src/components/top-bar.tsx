'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { type ReactNode } from 'react';
import {
  Badge,
  Tab,
  TabList,
  Title3,
  makeStyles,
  tokens,
} from '@fluentui/react-components';

export type TopBarPage = 'analytics' | 'dilution';

const useStyles = makeStyles({
  bar: {
    position: 'sticky',
    top: 0,
    zIndex: 10,
    height: '64px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: tokens.spacingHorizontalL,
    padding: `0 ${tokens.spacingHorizontalXL}`,
    backgroundColor: tokens.colorNeutralBackground1,
    borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
    backdropFilter: 'saturate(180%) blur(8px)',
    boxShadow: tokens.shadow2,
  },
  left: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacingHorizontalL,
    minWidth: 0,
  },
  brand: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacingHorizontalM,
    minWidth: 0,
    textDecoration: 'none',
    color: 'inherit',
  },
  monogram: {
    width: '36px',
    height: '36px',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: tokens.borderRadiusMedium,
    background: `linear-gradient(135deg, ${tokens.colorBrandBackground} 0%, ${tokens.colorBrandBackgroundHover} 100%)`,
    color: tokens.colorNeutralForegroundOnBrand,
    fontWeight: tokens.fontWeightBold,
    fontSize: '14px',
    letterSpacing: '-0.02em',
    boxShadow: tokens.shadow4Brand,
    flexShrink: 0,
  },
  title: {
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  right: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacingHorizontalM,
    flexShrink: 0,
  },
  badges: {
    display: 'flex',
    gap: tokens.spacingHorizontalXS,
    flexWrap: 'nowrap',
  },
});

type Props = {
  active: TopBarPage;
  lastUpdated: { finishedAt: Date | null; standingsCount: number | null } | null;
  rightSlot?: ReactNode;
};

export function TopBar({ active, lastUpdated, rightSlot }: Props) {
  const s = useStyles();
  const router = useRouter();

  return (
    <header className={s.bar}>
      <div className={s.left}>
        <Link href="/" className={s.brand}>
          <span className={s.monogram} aria-hidden>
            HC
          </span>
          <Title3 as="h1" className={s.title}>
            Hockey Calgary Analytics
          </Title3>
        </Link>
        <TabList
          selectedValue={active}
          appearance="subtle"
          size="medium"
          onTabSelect={(_, data) =>
            router.push(data.value === 'dilution' ? '/dilution' : '/')
          }
        >
          <Tab value="analytics">Analytics</Tab>
          <Tab value="dilution">Tier 1 Dilution</Tab>
        </TabList>
      </div>
      <div className={s.right}>
        <div className={s.badges}>
          {lastUpdated?.finishedAt ? (
            <Badge appearance="tint" color="informative">
              Updated {new Date(lastUpdated.finishedAt).toLocaleDateString()}
            </Badge>
          ) : (
            <Badge appearance="tint" color="warning">
              No scrape yet
            </Badge>
          )}
          {lastUpdated?.standingsCount != null && (
            <Badge appearance="tint" color="subtle">
              {lastUpdated.standingsCount.toLocaleString()} standings
            </Badge>
          )}
        </div>
        {rightSlot}
      </div>
    </header>
  );
}
