'use client';

import { useCallback, useMemo, useState } from 'react';
import {
  Body1,
  Caption1,
  LargeTitle,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import type { StandingRow } from '@/lib/analytics/data';
import { TIER_ORDER, type TierLabel } from '@/lib/analytics/tiering';
import {
  computeDilution,
  DILUTION_METRIC_LABELS,
  type DilutionFilterState,
  type DilutionMetricLabel,
} from '@/lib/analytics/dilution';
import { type Division } from '@/lib/analytics/communities';
import {
  getArray,
  putArrayIfChanged,
  sameArr,
  useUrlFilterState,
} from '@/lib/url-filter-state';
import { TopBar } from '@/components/top-bar';
import { AdminPanel, type ScraperRun } from '@/components/admin-panel';
import { DriftBanner, type SerializedDrift } from '@/components/drift-banner';
import { CoveragePopover } from '@/components/coverage-popover';
import { ScrapeProgressBanner } from '@/components/scrape-progress';
import { FilterShell } from '@/components/filter-shell';
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
  topbar: { gridArea: 'topbar' },
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

  const encode = useCallback(
    (s: DilutionFilterState, d: DilutionFilterState): URLSearchParams => {
      const p = new URLSearchParams();
      if (s.metric !== d.metric) p.set('metric', s.metric);
      putArrayIfChanged(p, 'seasons', s.seasons, d.seasons);
      putArrayIfChanged(p, 'types', s.types, d.types);
      putArrayIfChanged(p, 'ages', s.ages, d.ages);
      putArrayIfChanged(p, 'tiers', s.tiers, d.tiers);
      if (s.division !== d.division) p.set('division', s.division);
      putArrayIfChanged(p, 'communities', s.communities, d.communities);
      return p;
    },
    [],
  );

  const decode = useCallback(
    (p: URLSearchParams, d: DilutionFilterState): DilutionFilterState => ({
      metric: (p.get('metric') as DilutionMetricLabel) ?? d.metric,
      seasons: getArray(p, 'seasons', d.seasons),
      types: getArray(p, 'types', d.types),
      ages: getArray(p, 'ages', d.ages),
      tiers: getArray(p, 'tiers', d.tiers),
      division: (p.get('division') as Division) ?? d.division,
      communities: getArray(p, 'communities', d.communities),
    }),
    [],
  );

  const [state, setState] = useUrlFilterState(defaultState, encode, decode);
  const [navOpen, setNavOpen] = useState(false);
  const closeNav = () => setNavOpen(false);

  const result = useMemo(() => computeDilution(rows, state), [rows, state]);

  const activeCount =
    (state.metric !== defaultState.metric ? 1 : 0) +
    (sameArr(state.seasons, defaultState.seasons) ? 0 : 1) +
    (sameArr(state.types, defaultState.types) ? 0 : 1) +
    (sameArr(state.ages, defaultState.ages) ? 0 : 1) +
    (sameArr(state.tiers, defaultState.tiers) ? 0 : 1) +
    (state.division !== defaultState.division ? 1 : 0) +
    (sameArr(state.communities, defaultState.communities) ? 0 : 1);

  return (
    <div className={s.shell}>
      <div className={s.topbar}>
        <TopBar
          active="dilution"
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
            label: 'Performance metric',
            value: state.metric,
            options: DILUTION_METRIC_LABELS,
            onChange: (next) =>
              setState({ ...state, metric: next as DilutionMetricLabel }),
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
            values: state.tiers as TierLabel[],
            options: allTiers,
            onChange: (next) => setState({ ...state, tiers: next }),
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
