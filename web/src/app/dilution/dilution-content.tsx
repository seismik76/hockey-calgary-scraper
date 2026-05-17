'use client';

import { useMemo, useState } from 'react';
import {
  Body1,
  Caption1,
  LargeTitle,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import type { StandingRow } from '@/lib/analytics/data';
import { TIER_ORDER } from '@/lib/analytics/tiering';
import {
  computeDilution,
  type DilutionFilterState,
} from '@/lib/analytics/dilution';
import { TopBar } from '@/components/top-bar';
import { AdminPanel, type ScraperRun } from '@/components/admin-panel';
import { DriftBanner, type SerializedDrift } from '@/components/drift-banner';
import { CoveragePopover } from '@/components/coverage-popover';
import { ScrapeProgressBanner } from '@/components/scrape-progress';
import { DilutionFilters } from './dilution-filters';
import { HeadlineResult } from './headline-result';
import { ThresholdTable } from './threshold-table';
import { CliffChart } from './cliff-chart';
import { AggressivenessChart } from './aggressiveness-chart';

type Props = {
  rows: StandingRow[];
  lastUpdated: { finishedAt: Date | null; standingsCount: number | null } | null;
  drift: SerializedDrift | null;
  adminEnabled: boolean;
  isAdmin: boolean;
  initialRun: ScraperRun | null;
};

const TOPBAR_HEIGHT = 64;

const useStyles = makeStyles({
  shell: {
    display: 'grid',
    gridTemplateColumns: '340px minmax(0, 1fr)',
    gridTemplateRows: 'auto 1fr',
    gridTemplateAreas: `
      "topbar topbar"
      "sidebar main"
    `,
    minHeight: '100vh',
    backgroundColor: tokens.colorNeutralBackground2,
  },
  topbar: { gridArea: 'topbar' },
  sidebar: { gridArea: 'sidebar' },
  mainCol: {
    gridArea: 'main',
    minWidth: 0,
  },
  main: {
    padding: `${tokens.spacingVerticalXXL} ${tokens.spacingHorizontalXXL}`,
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacingVerticalXXL,
    width: '100%',
    maxWidth: '1320px',
    margin: '0 auto',
    boxSizing: 'border-box',
  },
  header: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacingVerticalS,
    maxWidth: '820px',
  },
  description: {
    color: tokens.colorNeutralForeground2,
    fontSize: '15px',
    lineHeight: '1.55',
  },
  footer: {
    paddingTop: tokens.spacingVerticalL,
    borderTop: `1px solid ${tokens.colorNeutralStroke2}`,
    color: tokens.colorNeutralForeground3,
  },
  emptyCard: {
    backgroundColor: tokens.colorNeutralBackground1,
    borderRadius: tokens.borderRadiusXLarge,
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    padding: tokens.spacingHorizontalXXL,
    textAlign: 'center',
    color: tokens.colorNeutralForeground2,
  },
});

export function DilutionContent({
  rows,
  lastUpdated,
  drift,
  adminEnabled,
  isAdmin,
  initialRun,
}: Props) {
  const s = useStyles();

  const allSeasons = useMemo(
    () => Array.from(new Set(rows.map((r) => r.season))).sort().reverse(),
    [rows],
  );
  const allTypes = useMemo(() => Array.from(new Set(rows.map((r) => r.type))), [rows]);
  const allAges = useMemo(
    () => Array.from(new Set(rows.map((r) => r.ageCategory))).sort(),
    [rows],
  );
  const allTiers = useMemo(() => {
    const present = new Set(rows.map((r) => r.tier));
    return TIER_ORDER.filter((t) => present.has(t));
  }, [rows]);
  const allCommunities = useMemo(
    () =>
      Array.from(
        new Set(rows.map((r) => r.community).filter((c): c is string => Boolean(c))),
      ).sort(),
    [rows],
  );

  const defaultState = useMemo<DilutionFilterState>(
    () => ({
      metric: 'Points %',
      seasons: allSeasons.slice(0, 2),
      types: ['Regular', 'Seeding'].filter((t) => allTypes.includes(t)),
      ages: ['U11', 'U13'].filter((a) => allAges.includes(a)),
      tiers: allTiers,
      division: 'All',
      communities: allCommunities,
    }),
    [allSeasons, allTypes, allAges, allTiers, allCommunities],
  );

  const [state, setState] = useState<DilutionFilterState>(defaultState);

  const result = useMemo(() => computeDilution(rows, state), [rows, state]);

  return (
    <div className={s.shell}>
      <div className={s.topbar}>
        <TopBar
          active="dilution"
          lastUpdated={lastUpdated}
          rightSlot={
            <>
              <CoveragePopover rows={rows} />
              <AdminPanel
                adminEnabled={adminEnabled}
                initialIsAdmin={isAdmin}
                initialRun={initialRun}
              />
            </>
          }
        />
      </div>

      <div className={s.sidebar}>
        <DilutionFilters
          stickyTop={TOPBAR_HEIGHT}
          state={state}
          setState={setState}
          defaultState={defaultState}
          allSeasons={allSeasons}
          allTypes={allTypes}
          allAges={allAges}
          allTiers={allTiers}
          allCommunities={allCommunities}
        />
      </div>

      <div className={s.mainCol}>
        <main className={s.main}>
          <ScrapeProgressBanner initialRun={initialRun} />
          <DriftBanner drift={drift} />
          <header className={s.header}>
            <LargeTitle as="h1" block>
              Tier 1 Dilution Analysis
            </LargeTitle>
            <Body1 className={s.description}>
              <strong>The claim:</strong> communities that just barely cross the threshold
              for fielding a <em>second</em> Tier 1 team underperform — not just at Tier 1,
              but <strong>across every tier</strong> in that age group. The talent pool gets
              split too thin.
            </Body1>
          </header>

          {result.communityStats.length === 0 ? (
            <div className={s.emptyCard}>
              <Body1>No data matches the selected filters.</Body1>
            </div>
          ) : (
            <>
              <HeadlineResult
                cohortStats={result.cohortStats}
                diluted={result.diluted}
                metricLabel={state.metric}
              />
              <ThresholdTable entries={result.thresholds} />
              <CliffChart
                communityStats={result.communityStats}
                cohortStats={result.cohortStats}
                metricLabel={state.metric}
              />
              <AggressivenessChart
                series={result.aggressivenessByCommunity}
                metricLabel={state.metric}
              />
            </>
          )}

          <footer className={s.footer}>
            <Caption1>
              Personal-interest project — not an authoritative source. Data scraped from
              Hockey Calgary, RAMP (Alberta One), and TeamLinkt.
            </Caption1>
          </footer>
        </main>
      </div>
    </div>
  );
}
