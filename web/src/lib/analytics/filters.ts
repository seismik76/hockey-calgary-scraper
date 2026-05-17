import type { StandingRow } from './data';
import type { Division } from './communities';
import type { MetricLabel } from './metrics';
import type { TierLabel } from './tiering';

export type FilterState = {
  metric: MetricLabel;
  seasons: string[];
  types: string[];
  ages: string[];
  tiers: TierLabel[];
  division: Division;
  communities: string[];
  leagues: string[];
  teams: string[];
};

export function applyFilters(rows: StandingRow[], f: FilterState): StandingRow[] {
  return rows.filter((r) => {
    if (f.seasons.length && !f.seasons.includes(r.season)) return false;
    if (f.types.length && !f.types.includes(r.type)) return false;
    if (f.ages.length && !f.ages.includes(r.ageCategory)) return false;
    if (f.tiers.length && !f.tiers.includes(r.tier)) return false;
    if (f.communities.length && (!r.community || !f.communities.includes(r.community))) return false;
    if (f.leagues.length && !f.leagues.includes(r.league)) return false;
    if (f.teams.length && !f.teams.includes(r.teamLabel)) return false;
    return true;
  });
}

export function uniqueSorted<T extends string | number>(values: Iterable<T>): T[] {
  return Array.from(new Set(values)).sort();
}
