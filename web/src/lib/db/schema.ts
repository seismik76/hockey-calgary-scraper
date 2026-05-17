import { pgTable, serial, integer, text, timestamp, unique } from 'drizzle-orm/pg-core';

export const seasons = pgTable('seasons', {
  id: serial('id').primaryKey(),
  name: text('name').notNull().unique(),
});

export const leagues = pgTable(
  'leagues',
  {
    id: serial('id').primaryKey(),
    name: text('name').notNull(),
    slug: text('slug').notNull(),
    stream: text('stream').notNull(),
    type: text('type').default('Regular'),
  },
  (t) => [unique('_league_slug_stream_type_uc').on(t.slug, t.stream, t.type)],
);

export const communities = pgTable('communities', {
  id: serial('id').primaryKey(),
  name: text('name').notNull().unique(),
});

export const teams = pgTable(
  'teams',
  {
    id: serial('id').primaryKey(),
    name: text('name').notNull(),
    communityId: integer('community_id').references(() => communities.id),
  },
  (t) => [unique('_team_name_uc').on(t.name)],
);

export const standings = pgTable(
  'standings',
  {
    id: serial('id').primaryKey(),
    seasonId: integer('season_id').notNull().references(() => seasons.id),
    leagueId: integer('league_id').notNull().references(() => leagues.id),
    teamId: integer('team_id').notNull().references(() => teams.id),
    communityId: integer('community_id').references(() => communities.id),
    gp: integer('gp'),
    w: integer('w'),
    l: integer('l'),
    t: integer('t'),
    pts: integer('pts'),
    gf: integer('gf'),
    ga: integer('ga'),
    diff: integer('diff'),
    sourceUrl: text('source_url'),
  },
  (t) => [unique('_standing_uc').on(t.seasonId, t.leagueId, t.teamId)],
);

export const scrapeRuns = pgTable('scrape_runs', {
  id: serial('id').primaryKey(),
  startedAt: timestamp('started_at').notNull().defaultNow(),
  finishedAt: timestamp('finished_at'),
  status: text('status').notNull().default('running'),
  errorMessage: text('error_message'),
  leaguesProcessed: integer('leagues_processed'),
  leaguesFailed: integer('leagues_failed'),
  failedLeagues: text('failed_leagues'),
  standingsCount: integer('standings_count'),
});
