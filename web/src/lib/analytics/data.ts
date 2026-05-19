import 'server-only';
import { sql } from 'drizzle-orm';
import { db } from '@/lib/db';
import { extractTierLabel, type TierLabel } from './tiering';
import { standardizeTeamLabel } from './team-labels';

export type StandingRow = {
  seasonId: number;
  leagueId: number;
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
  SeasonId: number;
  LeagueId: number;
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

const BASE_SELECT = sql`
  SELECT
      s.id as "SeasonId",
      l.id as "LeagueId",
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
    seasonId: r.SeasonId,
    leagueId: r.LeagueId,
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
  const result = await db.execute(BASE_SELECT);
  const rows = (result.rows as unknown as Raw[])
    .map(enrichRow)
    // Exclude Girls Hockey Calgary from headline analytics (parity with Streamlit).
    .filter((r) => r.community !== 'Girls Hockey Calgary');
  return rows;
}

export type LeagueIndexEntry = {
  seasonId: number;
  leagueId: number;
  season: string;
  league: string;
  type: string;
  stream: string;
  ageCategory: string;
  tier: TierLabel;
  teamCount: number;
};

// One row per (season, league) pair that has at least one non-GHC standings
// row. Girls Hockey Calgary is excluded everywhere in the app — leagues whose
// only standings are GHC drop out entirely; mixed leagues just show a smaller
// team count.
export async function loadLeagueIndex(): Promise<LeagueIndexEntry[]> {
  const result = await db.execute(sql`
    SELECT
      s.id as "SeasonId",
      l.id as "LeagueId",
      s.name as "Season",
      l.name as "League",
      l.type as "Type",
      l.stream as "Stream",
      COUNT(*)::int as "TeamCount"
    FROM standings st
    JOIN seasons s ON st.season_id = s.id
    JOIN leagues l ON st.league_id = l.id
    JOIN teams t ON st.team_id = t.id
    LEFT JOIN communities c_st ON st.community_id = c_st.id
    LEFT JOIN communities c_t ON t.community_id = c_t.id
    WHERE COALESCE(c_st.name, c_t.name) IS DISTINCT FROM 'Girls Hockey Calgary'
    GROUP BY s.id, l.id, s.name, l.name, l.type, l.stream
  `);
  type Row = {
    SeasonId: number;
    LeagueId: number;
    Season: string;
    League: string;
    Type: string;
    Stream: string;
    TeamCount: number;
  };
  const rows = (result.rows as unknown as Row[]).map<LeagueIndexEntry>((r) => {
    const ageMatch = r.League?.match(/U\d{1,2}/);
    return {
      seasonId: r.SeasonId,
      leagueId: r.LeagueId,
      season: r.Season,
      league: r.League,
      type: r.Type,
      stream: r.Stream,
      ageCategory: ageMatch ? ageMatch[0] : 'Other',
      tier: extractTierLabel(r.League),
      teamCount: r.TeamCount,
    };
  });
  return rows;
}

export type LeagueGame = {
  id: number;
  playedAt: Date | null;
  homeTeam: string;
  awayTeam: string;
  homeTeamLabel: string;
  awayTeamLabel: string;
  homeCommunity: string | null;
  awayCommunity: string | null;
  homeScore: number;
  awayScore: number;
  venue: string | null;
  gameType: string;
  source: string;
  sourceUrl: string | null;
};

type RawGame = {
  Id: number;
  PlayedAt: Date | string | null;
  HomeTeam: string;
  AwayTeam: string;
  HomeCommunity: string | null;
  AwayCommunity: string | null;
  League: string;
  HomeScore: number;
  AwayScore: number;
  Venue: string | null;
  GameType: string;
  Source: string;
  SourceUrl: string | null;
};

// Completed games for a single (season, league) — sorted by date ascending.
export async function loadLeagueGames(
  seasonId: number,
  leagueId: number,
): Promise<LeagueGame[]> {
  const result = await db.execute(sql`
    SELECT
        g.id as "Id",
        g.played_at as "PlayedAt",
        ht.name as "HomeTeam",
        at_.name as "AwayTeam",
        hc.name as "HomeCommunity",
        ac.name as "AwayCommunity",
        l.name as "League",
        g.home_score as "HomeScore",
        g.away_score as "AwayScore",
        g.venue as "Venue",
        g.game_type as "GameType",
        g.source as "Source",
        g.source_url as "SourceUrl"
    FROM games g
    JOIN teams ht ON g.home_team_id = ht.id
    JOIN teams at_ ON g.away_team_id = at_.id
    JOIN leagues l ON g.league_id = l.id
    LEFT JOIN communities hc ON ht.community_id = hc.id
    LEFT JOIN communities ac ON at_.community_id = ac.id
    WHERE g.season_id = ${seasonId} AND g.league_id = ${leagueId}
    ORDER BY g.played_at NULLS LAST, g.id
  `);

  return (result.rows as unknown as RawGame[]).map((r) => ({
    id: r.Id,
    playedAt: r.PlayedAt ? new Date(r.PlayedAt as string) : null,
    homeTeam: r.HomeTeam,
    awayTeam: r.AwayTeam,
    homeTeamLabel: standardizeTeamLabel(r.HomeTeam, r.League, r.HomeCommunity),
    awayTeamLabel: standardizeTeamLabel(r.AwayTeam, r.League, r.AwayCommunity),
    homeCommunity: r.HomeCommunity,
    awayCommunity: r.AwayCommunity,
    homeScore: r.HomeScore,
    awayScore: r.AwayScore,
    venue: r.Venue,
    gameType: r.GameType,
    source: r.Source,
    sourceUrl: r.SourceUrl,
  }));
}

export type CommunityAggregateRow = {
  community: string;
  teamCount: number;
  gp: number;
  w: number;
  l: number;
  t: number;
  pts: number;
  gf: number;
  ga: number;
  diff: number;
};

// Aggregate W / L / GF / GA / diff per community across every team that
// belongs to the given age group in the given season. Excludes AA/HADP
// (elite tiers), Girls Hockey Calgary, and any non-Regular league types
// (Seeding / Playoff / Tournament don't count toward season standings).
export async function loadCommunityAggregates(
  age: string,
  season: string,
): Promise<CommunityAggregateRow[]> {
  const ageUpper = age.toUpperCase();
  const result = await db.execute(sql`
    WITH eligible AS (
      SELECT
        COALESCE(c_st.name, c_t.name) AS community,
        st.team_id,
        st.gp, st.w, st.l, st.t, st.pts, st.gf, st.ga, st.diff
      FROM standings st
      JOIN seasons s ON st.season_id = s.id
      JOIN leagues l ON st.league_id = l.id
      JOIN teams t ON st.team_id = t.id
      LEFT JOIN communities c_st ON st.community_id = c_st.id
      LEFT JOIN communities c_t ON t.community_id = c_t.id
      WHERE s.name = ${season}
        AND l.name ~* ${'\\m' + ageUpper + '\\M'}
        AND l.type = 'Regular'
        AND l.name !~* 'AA|HADP'
        AND COALESCE(c_st.name, c_t.name) IS NOT NULL
        AND COALESCE(c_st.name, c_t.name) != 'Girls Hockey Calgary'
    )
    SELECT
      community,
      COUNT(DISTINCT team_id)::int AS team_count,
      COALESCE(SUM(gp), 0)::int  AS gp,
      COALESCE(SUM(w), 0)::int   AS w,
      COALESCE(SUM(l), 0)::int   AS l,
      COALESCE(SUM(t), 0)::int   AS t,
      COALESCE(SUM(pts), 0)::int AS pts,
      COALESCE(SUM(gf), 0)::int  AS gf,
      COALESCE(SUM(ga), 0)::int  AS ga,
      COALESCE(SUM(diff), 0)::int AS diff
    FROM eligible
    GROUP BY community
    ORDER BY diff DESC, w DESC, community
  `);

  return (result.rows as unknown as Array<{
    community: string;
    team_count: number;
    gp: number; w: number; l: number; t: number; pts: number;
    gf: number; ga: number; diff: number;
  }>).map((r) => ({
    community: r.community,
    teamCount: r.team_count,
    gp: r.gp, w: r.w, l: r.l, t: r.t, pts: r.pts,
    gf: r.gf, ga: r.ga, diff: r.diff,
  }));
}

// Distinct season names where there is at least one Regular standings row
// for the given age (excluding AA/HADP and GHC). Used to populate the season
// selector on /communities/[age] without hardcoding 2025-2026.
export async function loadAvailableSeasons(age: string): Promise<string[]> {
  const ageUpper = age.toUpperCase();
  const result = await db.execute(sql`
    SELECT DISTINCT s.name AS season
    FROM standings st
    JOIN seasons s ON st.season_id = s.id
    JOIN leagues l ON st.league_id = l.id
    JOIN teams t ON st.team_id = t.id
    LEFT JOIN communities c_st ON st.community_id = c_st.id
    LEFT JOIN communities c_t ON t.community_id = c_t.id
    WHERE l.name ~* ${'\\m' + ageUpper + '\\M'}
      AND l.type = 'Regular'
      AND l.name !~* 'AA|HADP'
      AND COALESCE(c_st.name, c_t.name) IS NOT NULL
      AND COALESCE(c_st.name, c_t.name) != 'Girls Hockey Calgary'
      AND s.name >= '2025-2026'
    ORDER BY season DESC
  `);
  return (result.rows as unknown as Array<{ season: string }>).map((r) => r.season);
}

export type LeagueDetail = {
  seasonId: number;
  leagueId: number;
  season: string;
  league: string;
  type: string;
  stream: string;
  ageCategory: string;
  tier: TierLabel;
  sourceUrl: string | null;
  rows: StandingRow[];
};

// Pulls every team-row for a single (season, league) pair, sorted by points
// then goal differential. Returns null if no standings exist for that pair.
export async function loadLeagueDetail(
  seasonId: number,
  leagueId: number,
): Promise<LeagueDetail | null> {
  const result = await db.execute(sql`
    ${BASE_SELECT}
    WHERE st.season_id = ${seasonId} AND st.league_id = ${leagueId}
  `);
  const rows = (result.rows as unknown as Raw[]).map(enrichRow);
  if (rows.length === 0) return null;

  rows.sort((a, b) => {
    const pa = a.pts ?? -Infinity;
    const pb = b.pts ?? -Infinity;
    if (pa !== pb) return pb - pa;
    const da = a.diff ?? -Infinity;
    const db_ = b.diff ?? -Infinity;
    if (da !== db_) return db_ - da;
    return (b.gf ?? 0) - (a.gf ?? 0);
  });

  const head = rows[0];
  // Pick the first non-null source_url — they should all match for a given
  // (season, league) since the scraper writes one upstream page per league.
  const sourceUrl = rows.find((r) => r.source)?.source ?? null;

  return {
    seasonId: head.seasonId,
    leagueId: head.leagueId,
    season: head.season,
    league: head.league,
    type: head.type,
    stream: head.stream,
    ageCategory: head.ageCategory,
    tier: head.tier,
    sourceUrl,
    rows,
  };
}
