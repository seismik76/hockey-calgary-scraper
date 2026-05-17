import 'server-only';
import { sql } from 'drizzle-orm';
import { db } from '@/lib/db';
import { extractTierLabel, type TierLabel } from './tiering';
import { standardizeTeamLabel } from './team-labels';

export type StandingRow = {
  season: string;
  league: string;
  type: string;
  stream: string;
  community: string | null;
  team: string;
  gp: number | null;
  w: number | null;
  l: number | null;
  t: number | null;
  pts: number | null;
  gf: number | null;
  ga: number | null;
  diff: number | null;
  source: string | null;
  // Derived:
  winPct: number;
  pointsPct: number;
  goalDiffPerGame: number;
  ageCategory: string;
  tier: TierLabel;
  teamLabel: string;
};

type Raw = {
  Season: string;
  League: string;
  Type: string;
  Stream: string;
  Community: string | null;
  Team: string;
  GP: number | null;
  W: number | null;
  L: number | null;
  T: number | null;
  PTS: number | null;
  GF: number | null;
  GA: number | null;
  Diff: number | null;
  Source: string | null;
};

const QUERY = sql`
  SELECT
      s.name as "Season",
      l.name as "League",
      l.type as "Type",
      l.stream as "Stream",
      COALESCE(c_st.name, c_t.name) as "Community",
      t.name as "Team",
      st.gp as "GP",
      st.w as "W",
      st.l as "L",
      st.t as "T",
      st.pts as "PTS",
      st.gf as "GF",
      st.ga as "GA",
      st.diff as "Diff",
      st.source_url as "Source"
  FROM standings st
  JOIN seasons s ON st.season_id = s.id
  JOIN leagues l ON st.league_id = l.id
  JOIN teams t ON st.team_id = t.id
  LEFT JOIN communities c_st ON st.community_id = c_st.id
  LEFT JOIN communities c_t ON t.community_id = c_t.id
`;

function enrichRow(r: Raw): StandingRow {
  const gp = r.GP ?? 0;
  const w = r.W ?? 0;
  const pts = r.PTS ?? 0;
  const diff = r.Diff ?? 0;
  const positive = gp > 0;

  const ageMatch = r.League?.match(/U\d{1,2}/);
  const ageCategory = ageMatch ? ageMatch[0] : 'Other';

  return {
    season: r.Season,
    league: r.League,
    type: r.Type,
    stream: r.Stream,
    community: r.Community,
    team: r.Team,
    gp: r.GP,
    w: r.W,
    l: r.L,
    t: r.T,
    pts: r.PTS,
    gf: r.GF,
    ga: r.GA,
    diff: r.Diff,
    source: r.Source,
    winPct: positive ? w / gp : 0,
    pointsPct: positive ? pts / (gp * 2) : 0,
    goalDiffPerGame: positive ? diff / gp : 0,
    ageCategory,
    tier: extractTierLabel(r.League),
    teamLabel: standardizeTeamLabel(r.Team, r.League, r.Community),
  };
}

export async function loadStandings(): Promise<StandingRow[]> {
  const result = await db.execute(QUERY);
  const rows = (result.rows as unknown as Raw[])
    .map(enrichRow)
    // Exclude Girls Hockey Calgary from headline analytics (parity with Streamlit).
    .filter((r) => r.community !== 'Girls Hockey Calgary');
  return rows;
}
