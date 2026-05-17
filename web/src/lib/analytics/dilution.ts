import type { StandingRow } from './data';
import type { Division } from './communities';
import { parseTierInfo } from './tiering';

export const DILUTION_METRICS = {
  'Points %': 'pointsPct',
  'Win %': 'winPct',
  'Goal Diff/Game': 'goalDiffPerGame',
} as const;

export type DilutionMetricLabel = keyof typeof DILUTION_METRICS;
export type DilutionMetricKey = (typeof DILUTION_METRICS)[DilutionMetricLabel];

export const DILUTION_METRIC_LABELS = Object.keys(DILUTION_METRICS) as DilutionMetricLabel[];

export type DilutionFilterState = {
  metric: DilutionMetricLabel;
  seasons: string[];
  types: string[];
  ages: string[];
  tiers: string[];
  division: Division;
  communities: string[];
};

export type Category =
  | 'Small (1 Team)'
  | 'Just Below Threshold (1 Team)'
  | 'Just Above Threshold (Diluted)'
  | 'Large (Established)'
  | 'Other';

export const COHORT_CATEGORIES: Exclude<Category, 'Other'>[] = [
  'Small (1 Team)',
  'Just Below Threshold (1 Team)',
  'Just Above Threshold (Diluted)',
  'Large (Established)',
];

export const COHORT_SHORT: Record<Exclude<Category, 'Other'>, string> = {
  'Small (1 Team)': 'Small',
  'Just Below Threshold (1 Team)': 'Just Below',
  'Just Above Threshold (Diluted)': 'Just Above (Diluted)',
  'Large (Established)': 'Large',
};

// Colour scheme matches the Streamlit version:
//   Small / Just Below = green (healthy 1 T1)
//   Just Above (Diluted) = red (the hypothesis)
//   Large = blue (healthy 2+ T1)
export const COHORT_COLORS: Record<Exclude<Category, 'Other'>, string> = {
  'Small (1 Team)': '#86c486',
  'Just Below Threshold (1 Team)': '#2ca02c',
  'Just Above Threshold (Diluted)': '#d62728',
  'Large (Established)': '#1f77b4',
};

export type CommunityStat = {
  season: string;
  community: string;
  ageCategory: string;
  totalTeams: number;
  tier1Count: number;
  overallPerformance: number;
  category: Category;
  label: string;
};

export type ThresholdEntry = {
  season: string;
  ageCategory: string;
  threshold: number; // 999 if no 2+ Tier 1 communities exist
  outliers: string[];
};

export type CohortStat = {
  category: Exclude<Category, 'Other'>;
  mean: number | null;
  count: number;
};

export type AggressivenessPoint = {
  community: string;
  season: string;
  seasonShort: string; // e.g. "'24" for trend label
  aggressiveness: number; // [0, 1]
  performance: number;
  totalTeams: number;
  tier1Count: number;
};

export type DilutionResult = {
  thresholds: ThresholdEntry[];
  communityStats: CommunityStat[];
  cohortStats: CohortStat[];
  aggressivenessByCommunity: { community: string; points: AggressivenessPoint[] }[];
  /** Aggregated delta of Diluted vs avg(neighbours) — the headline test. */
  diluted: {
    mean: number;
    count: number;
    deltaVsNeighbours: number | null;
    neighbourMean: number | null;
  };
};

function isElite(leagueName: string): boolean {
  const upper = leagueName.toUpperCase();
  return upper.includes('AA') || upper.includes('HADP');
}

function isTier1Pure(leagueName: string): boolean {
  // Pure Tier 1, excluding NBC and AA/HADP.
  const info = parseTierInfo(leagueName);
  return info.tier === 1 && info.stream !== 'NBC';
}

const COMMUNITY_ABBREV: Record<string, string> = {
  'Bow River': 'BR',
  'Bow Valley': 'BV',
  Glenlake: 'GL',
  Knights: 'K',
  McKnight: 'MK',
  'North West': 'NW',
  Raiders: 'R',
  Southwest: 'SW',
  Springbank: 'SB',
  'Trails West': 'TW',
  Wolverines: 'W',
};

function shortSeason(season: string): string {
  // "2023-2024" → "'24"
  const parts = season.split('-');
  const last = parts[parts.length - 1];
  return `'${last.slice(-2)}`;
}

function makeLabel(season: string, community: string, age: string) {
  const abbrev = COMMUNITY_ABBREV[community] ?? community.slice(0, 2).toUpperCase();
  return `${abbrev}-${shortSeason(season).slice(1)} (${age})`;
}

function categorize(
  size: number,
  tier1: number,
  threshold: number,
): Category {
  if (tier1 === 1) {
    if (size >= threshold - 3) return 'Just Below Threshold (1 Team)';
    return 'Small (1 Team)';
  }
  if (tier1 >= 2) {
    if (size >= threshold && size <= threshold + 1) return 'Just Above Threshold (Diluted)';
    return 'Large (Established)';
  }
  return 'Other';
}

/** Group rows by composite key, applying a mapper to each row. */
function groupBy<T, K extends string>(
  rows: T[],
  keyFn: (row: T) => K,
): Map<K, T[]> {
  const m = new Map<K, T[]>();
  for (const r of rows) {
    const k = keyFn(r);
    const existing = m.get(k);
    if (existing) existing.push(r);
    else m.set(k, [r]);
  }
  return m;
}

function unique<T>(values: Iterable<T>): T[] {
  return Array.from(new Set(values));
}

/**
 * Brute-force search for the team-count threshold that best separates
 * "1 Tier 1" communities from "2+ Tier 1" communities in a (season, age) group.
 * Mirrors the algorithm in app.py: maximise the number of compliant communities.
 */
function inferThreshold(
  group: Array<{ community: string; totalTeams: number; tier1Count: number }>,
): { threshold: number; outliers: string[] } {
  if (group.length === 0) return { threshold: 0, outliers: [] };
  const maxT1 = Math.max(...group.map((g) => g.tier1Count));
  if (maxT1 < 2) return { threshold: 999, outliers: [] };

  const min = Math.min(...group.map((g) => g.totalTeams));
  const max = Math.max(...group.map((g) => g.totalTeams));

  let bestT = min;
  let bestScore = -1;
  let bestOutliers: typeof group = [];

  for (let t = min; t <= max + 1; t++) {
    const compliant = group.filter(
      (g) =>
        (g.totalTeams < t && g.tier1Count <= 1) ||
        (g.totalTeams >= t && g.tier1Count >= 2),
    );
    if (compliant.length > bestScore) {
      bestScore = compliant.length;
      bestT = t;
      bestOutliers = group.filter((g) => !compliant.includes(g));
    }
  }

  return {
    threshold: bestT,
    outliers: bestOutliers.map(
      (o) => `${o.community} (${o.totalTeams} teams, ${o.tier1Count} T1)`,
    ),
  };
}

/** Per (season, community, age) — count of non-elite teams + count of Tier 1 (pure). */
type SizeAndT1 = {
  season: string;
  community: string;
  ageCategory: string;
  totalTeams: number;
  tier1Count: number;
};

function buildSizeAndT1(rows: StandingRow[]): SizeAndT1[] {
  // Count unique team names per (season, community, age) for non-elite + tier1.
  const sizes = new Map<string, Set<string>>();
  const t1s = new Map<string, Set<string>>();

  for (const r of rows) {
    if (!r.community) continue;
    const key = `${r.season}|${r.community}|${r.ageCategory}`;

    if (!isElite(r.league)) {
      let s = sizes.get(key);
      if (!s) {
        s = new Set();
        sizes.set(key, s);
      }
      s.add(r.team);
    }
    if (isTier1Pure(r.league)) {
      let s = t1s.get(key);
      if (!s) {
        s = new Set();
        t1s.set(key, s);
      }
      s.add(r.team);
    }
  }

  const out: SizeAndT1[] = [];
  for (const [key, teams] of sizes) {
    const [season, community, ageCategory] = key.split('|');
    out.push({
      season,
      community,
      ageCategory,
      totalTeams: teams.size,
      tier1Count: t1s.get(key)?.size ?? 0,
    });
  }
  return out;
}

function weightedMean(
  rows: StandingRow[],
  metricKey: DilutionMetricKey,
): number {
  let weighted = 0;
  let totalGP = 0;
  for (const r of rows) {
    const gp = r.gp ?? 0;
    if (gp <= 0) continue;
    weighted += r[metricKey] * gp;
    totalGP += gp;
  }
  return totalGP > 0 ? weighted / totalGP : 0;
}

export function computeDilution(
  rows: StandingRow[],
  filters: DilutionFilterState,
): DilutionResult {
  const metricKey = DILUTION_METRICS[filters.metric];

  // (1) Threshold scope — by Type + Age only. Wider than the per-view filter
  // so the threshold is stable when the user narrows the community list.
  const fullScope = rows.filter(
    (r) =>
      filters.types.includes(r.type) && filters.ages.includes(r.ageCategory),
  );
  const fullSizeT1 = buildSizeAndT1(fullScope);

  // (2) Infer threshold per (season, age) from fullScope.
  const thresholdMap = new Map<string, ThresholdEntry>();
  const fullGroups = groupBy(fullSizeT1, (s) => `${s.season}|${s.ageCategory}`);
  for (const [key, group] of fullGroups) {
    const [season, ageCategory] = key.split('|');
    const inferred = inferThreshold(group);
    thresholdMap.set(key, {
      season,
      ageCategory,
      threshold: inferred.threshold,
      outliers: inferred.outliers,
    });
  }

  // (3) Analysis scope — apply all 6 filters.
  const analysisRows = rows.filter(
    (r) =>
      filters.seasons.includes(r.season) &&
      filters.types.includes(r.type) &&
      filters.ages.includes(r.ageCategory) &&
      (filters.tiers.length === 0 || filters.tiers.includes(r.tier)) &&
      (filters.communities.length === 0 ||
        (r.community && filters.communities.includes(r.community))),
  );

  // (4) Size + T1 count from analysisRows.
  const analysisSizeT1 = buildSizeAndT1(analysisRows);

  // (5) Weighted performance per (season, community, age) — non-elite only.
  const performanceMap = new Map<string, number>();
  const perfGroups = groupBy(
    analysisRows.filter((r) => !isElite(r.league)),
    (r) => `${r.season}|${r.community ?? ''}|${r.ageCategory}`,
  );
  for (const [key, group] of perfGroups) {
    performanceMap.set(key, weightedMean(group, metricKey));
  }

  // (6) Merge → CommunityStat[] with category.
  const communityStats: CommunityStat[] = [];
  for (const s of analysisSizeT1) {
    const key = `${s.season}|${s.community}|${s.ageCategory}`;
    const tk = `${s.season}|${s.ageCategory}`;
    const threshold = thresholdMap.get(tk)?.threshold ?? 999;
    const performance = performanceMap.get(key);
    if (performance === undefined) continue;
    communityStats.push({
      ...s,
      overallPerformance: performance,
      category: categorize(s.totalTeams, s.tier1Count, threshold),
      label: makeLabel(s.season, s.community, s.ageCategory),
    });
  }

  // (7) Cohort summary stats (mean + n per category).
  const cohortStats: CohortStat[] = COHORT_CATEGORIES.map((cat) => {
    const subset = communityStats.filter((s) => s.category === cat);
    const total = subset.reduce((sum, s) => sum + s.overallPerformance, 0);
    return {
      category: cat,
      mean: subset.length > 0 ? total / subset.length : null,
      count: subset.length,
    };
  });

  // (8) Aggressiveness time-series per community (avg across selected age categories).
  type AggKey = string;
  const aggGroups = groupBy(communityStats, (s): AggKey => `${s.season}|${s.community}`);
  const aggressivenessPoints: AggressivenessPoint[] = [];
  for (const [key, group] of aggGroups) {
    const [season, community] = key.split('|');
    const totalTeams = group.reduce((sum, g) => sum + g.totalTeams, 0);
    const tier1Count = group.reduce((sum, g) => sum + g.tier1Count, 0);
    const aggressiveness = totalTeams > 0 ? tier1Count / totalTeams : 0;
    const performance =
      group.reduce((sum, g) => sum + g.overallPerformance, 0) / group.length;
    aggressivenessPoints.push({
      community,
      season,
      seasonShort: shortSeason(season),
      aggressiveness,
      performance,
      totalTeams,
      tier1Count,
    });
  }
  const aggressivenessByCommunity = unique(
    aggressivenessPoints.map((p) => p.community),
  )
    .sort()
    .map((community) => ({
      community,
      points: aggressivenessPoints
        .filter((p) => p.community === community)
        .sort((a, b) => a.season.localeCompare(b.season)),
    }));

  // (9) Headline: Diluted mean + delta vs neighbours (avg of Below + Large).
  const dilutedStat = cohortStats.find(
    (c) => c.category === 'Just Above Threshold (Diluted)',
  );
  const belowStat = cohortStats.find(
    (c) => c.category === 'Just Below Threshold (1 Team)',
  );
  const largeStat = cohortStats.find(
    (c) => c.category === 'Large (Established)',
  );
  const neighbourMeans = [belowStat?.mean, largeStat?.mean].filter(
    (m): m is number => m !== null && m !== undefined,
  );
  const neighbourMean =
    neighbourMeans.length > 0
      ? neighbourMeans.reduce((a, b) => a + b, 0) / neighbourMeans.length
      : null;
  const deltaVsNeighbours =
    dilutedStat?.mean !== null &&
    dilutedStat?.mean !== undefined &&
    neighbourMean !== null
      ? dilutedStat.mean - neighbourMean
      : null;

  return {
    thresholds: Array.from(thresholdMap.values()).sort((a, b) => {
      if (a.season !== b.season) return b.season.localeCompare(a.season);
      return a.ageCategory.localeCompare(b.ageCategory);
    }),
    communityStats,
    cohortStats,
    aggressivenessByCommunity,
    diluted: {
      mean: dilutedStat?.mean ?? 0,
      count: dilutedStat?.count ?? 0,
      deltaVsNeighbours,
      neighbourMean,
    },
  };
}
