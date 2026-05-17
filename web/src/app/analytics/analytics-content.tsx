'use client';

import { useMemo, useState } from 'react';
import {
  Body1,
  Caption1,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import type { StandingRow } from '@/lib/analytics/data';
import { METRICS } from '@/lib/analytics/metrics';
import { applyFilters, uniqueSorted, type FilterState } from '@/lib/analytics/filters';
import { TIER_ORDER } from '@/lib/analytics/tiering';
import { FiltersPanel } from './filters-panel';
import { MetricCards } from './metric-cards';
import { RankingSection } from './ranking-section';
import { DetailTable } from './detail-table';
import { CsvButton } from './csv-button';
import { TopBar } from '@/components/top-bar';
import { AdminPanel, type ScraperRun } from '@/components/admin-panel';
import { DriftBanner, type SerializedDrift } from '@/components/drift-banner';
import { CoveragePopover } from '@/components/coverage-popover';
import { ScrapeProgressBanner } from '@/components/scrape-progress';

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
  topbar: {
    gridArea: 'topbar',
  },
  sidebar: {
    gridArea: 'sidebar',
  },
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

export function AnalyticsContent({
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

  const defaultState = useMemo<FilterState>(
    () => ({
      metric: 'Points',
      seasons: allSeasons.slice(0, 2),
      types: ['Regular', 'Seeding'].filter((t) => allTypes.includes(t)),
      ages: ['U11', 'U13'].filter((a) => allAges.includes(a)),
      tiers: allTiers,
      division: 'All',
      communities: allCommunities,
      leagues: [],
      teams: [],
    }),
    [allSeasons, allTypes, allAges, allTiers, allCommunities],
  );

  const [state, setState] = useState<FilterState>(defaultState);

  const availableLeagues = useMemo(() => {
    const partial = rows.filter(
      (r) =>
        (!state.seasons.length || state.seasons.includes(r.season)) &&
        (!state.types.length || state.types.includes(r.type)) &&
        (!state.ages.length || state.ages.includes(r.ageCategory)),
    );
    return uniqueSorted(partial.map((r) => r.league));
  }, [rows, state.seasons, state.types, state.ages]);

  const availableTeams = useMemo(() => {
    const partial = rows.filter(
      (r) =>
        !state.communities.length ||
        (r.community && state.communities.includes(r.community)),
    );
    return uniqueSorted(partial.map((r) => r.teamLabel));
  }, [rows, state.communities]);

  const filtered = useMemo(() => applyFilters(rows, state), [rows, state]);

  const summary = useMemo(
    () => [
      { label: 'Teams', value: new Set(filtered.map((r) => r.team)).size },
      { label: 'Leagues', value: new Set(filtered.map((r) => r.league)).size },
      { label: 'Seasons', value: new Set(filtered.map((r) => r.season)).size },
      {
        label: 'Communities',
        value: new Set(filtered.map((r) => r.community).filter(Boolean)).size,
      },
    ],
    [filtered],
  );

  const metricKey = METRICS[state.metric];

  return (
    <div className={s.shell}>
      <div className={s.topbar}>
        <TopBar
          active="analytics"
          lastUpdated={lastUpdated}
          rightSlot={
            <>
              <CoveragePopover rows={rows} />
              <AdminPanel
                adminEnabled={adminEnabled}
                initialIsAdmin={isAdmin}
                initialRun={initialRun}
              />
              <CsvButton all={rows} filtered={filtered} />
            </>
          }
        />
      </div>

      <div className={s.sidebar}>
        <FiltersPanel
          stickyTop={TOPBAR_HEIGHT}
          state={state}
          setState={setState}
          defaultState={defaultState}
          allSeasons={allSeasons}
          allTypes={allTypes}
          allAges={allAges}
          allTiers={allTiers}
          allCommunities={allCommunities}
          availableLeagues={availableLeagues}
          availableTeams={availableTeams}
        />
      </div>

      <div className={s.mainCol}>
        <main className={s.main}>
          <ScrapeProgressBanner initialRun={initialRun} />
          <DriftBanner drift={drift} />
          {filtered.length === 0 ? (
            <div className={s.emptyCard}>
              <Body1>No data matches the selected filters.</Body1>
            </div>
          ) : (
            <>
              <MetricCards stats={summary} />
              <RankingSection
                rows={filtered}
                metricLabel={state.metric}
                metricKey={metricKey}
              />
              <DetailTable rows={filtered} />
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
