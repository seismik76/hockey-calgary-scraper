'use client';

import { useCallback, useMemo, useState } from 'react';
import {
  Body1,
  Caption1,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import type { StandingRow } from '@/lib/analytics/data';
import { applyFilters, uniqueSorted, type FilterState } from '@/lib/analytics/filters';
import {
  getArray,
  putArrayIfChanged,
  sameArr,
  useUrlFilterState,
} from '@/lib/url-filter-state';
import { TIER_ORDER } from '@/lib/analytics/tiering';
import { FilterShell } from '@/components/filter-shell';
import { METRICS, METRIC_LABELS, type MetricLabel } from '@/lib/analytics/metrics';
import { type Division } from '@/lib/analytics/communities';
import { type TierLabel } from '@/lib/analytics/tiering';
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
    '@media (max-width: 900px)': {
      gridTemplateColumns: 'minmax(0, 1fr)',
      gridTemplateAreas: `
        "topbar"
        "main"
      `,
    },
  },
  topbar: {
    gridArea: 'topbar',
  },
  sidebar: {
    gridArea: 'sidebar',
    position: 'sticky',
    top: '64px',
    height: 'calc(100vh - 64px)',
    '@media (max-width: 900px)': {
      position: 'fixed',
      top: '64px',
      left: 0,
      bottom: 0,
      width: '320px',
      height: 'auto',
      zIndex: 30,
      transform: 'translateX(-100%)',
      transition: 'transform 0.22s ease',
      boxShadow: tokens.shadow16,
    },
  },
  sidebarOpen: {
    '@media (max-width: 900px)': {
      transform: 'translateX(0)',
    },
  },
  backdrop: {
    display: 'none',
    '@media (max-width: 900px)': {
      display: 'block',
      position: 'fixed',
      top: '64px',
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.42)',
      zIndex: 25,
      opacity: 0,
      pointerEvents: 'none',
      transition: 'opacity 0.22s ease',
    },
  },
  backdropOpen: {
    '@media (max-width: 900px)': {
      opacity: 1,
      pointerEvents: 'auto',
    },
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

  const encode = useCallback(
    (s: FilterState, d: FilterState): URLSearchParams => {
      const p = new URLSearchParams();
      if (s.metric !== d.metric) p.set('metric', s.metric);
      putArrayIfChanged(p, 'seasons', s.seasons, d.seasons);
      putArrayIfChanged(p, 'types', s.types, d.types);
      putArrayIfChanged(p, 'ages', s.ages, d.ages);
      putArrayIfChanged(p, 'tiers', s.tiers, d.tiers);
      if (s.division !== d.division) p.set('division', s.division);
      putArrayIfChanged(p, 'communities', s.communities, d.communities);
      if (s.leagues.length) p.set('leagues', s.leagues.join(','));
      if (s.teams.length) p.set('teams', s.teams.join(','));
      return p;
    },
    [],
  );

  const decode = useCallback(
    (p: URLSearchParams, d: FilterState): FilterState => ({
      metric: (p.get('metric') as MetricLabel) ?? d.metric,
      seasons: getArray(p, 'seasons', d.seasons),
      types: getArray(p, 'types', d.types),
      ages: getArray(p, 'ages', d.ages),
      tiers: getArray(p, 'tiers', d.tiers) as TierLabel[],
      division: (p.get('division') as Division) ?? d.division,
      communities: getArray(p, 'communities', d.communities),
      leagues: getArray(p, 'leagues', []),
      teams: getArray(p, 'teams', []),
    }),
    [],
  );

  const [state, setState] = useUrlFilterState(defaultState, encode, decode);
  const [navOpen, setNavOpen] = useState(false);
  const closeNav = () => setNavOpen(false);

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

  const activeCount =
    (state.metric !== defaultState.metric ? 1 : 0) +
    (sameArr(state.seasons, defaultState.seasons) ? 0 : 1) +
    (sameArr(state.types, defaultState.types) ? 0 : 1) +
    (sameArr(state.ages, defaultState.ages) ? 0 : 1) +
    (sameArr(state.tiers, defaultState.tiers) ? 0 : 1) +
    (state.division !== defaultState.division ? 1 : 0) +
    (sameArr(state.communities, defaultState.communities) ? 0 : 1) +
    (state.leagues.length ? 1 : 0) +
    (state.teams.length ? 1 : 0);

  return (
    <div className={s.shell}>
      <div className={s.topbar}>
        <TopBar
          active="analytics"
          lastUpdated={lastUpdated}
          onMenuClick={() => setNavOpen(true)}
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

      <div
        className={`${s.backdrop} ${navOpen ? s.backdropOpen : ''}`}
        onClick={closeNav}
        aria-hidden
      />

      <div className={`${s.sidebar} ${navOpen ? s.sidebarOpen : ''}`}>
        <FilterShell
          activeCount={activeCount}
          onReset={() => setState(defaultState)}
          metric={{
            value: state.metric,
            options: METRIC_LABELS,
            onChange: (next) => setState({ ...state, metric: next as MetricLabel }),
          }}
          seasons={{
            values: state.seasons,
            options: allSeasons,
            onChange: (next) => setState({ ...state, seasons: next }),
          }}
          types={{
            values: state.types,
            options: allTypes,
            onChange: (next) => setState({ ...state, types: next }),
          }}
          ages={{
            values: state.ages,
            options: allAges,
            onChange: (next) => setState({ ...state, ages: next }),
          }}
          tiers={{
            values: state.tiers,
            options: allTiers,
            onChange: (next) => setState({ ...state, tiers: next as TierLabel[] }),
          }}
          division={{
            value: state.division,
            allCommunities,
            onChange: (next: Division) => setState({ ...state, division: next }),
          }}
          communities={{
            values: state.communities,
            options: allCommunities,
            onChange: (next) => setState({ ...state, communities: next }),
          }}
          refine={{
            leagues: {
              values: state.leagues,
              options: availableLeagues,
              onChange: (next) => setState({ ...state, leagues: next }),
            },
            teams: {
              values: state.teams,
              options: availableTeams,
              onChange: (next) => setState({ ...state, teams: next }),
            },
          }}
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
