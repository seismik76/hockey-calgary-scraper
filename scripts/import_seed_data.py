"""
Import rows from the SQLite seed (data/seed/hockey_calgary.db) into the Postgres DB
pointed at by DATABASE_URL.

Live wins: standings whose (season, league, team) tuple already exists in the
destination are left untouched. Anything else from the seed gets inserted.

Idempotent — re-running adds nothing new once the seed has been merged in.

Usage:
    python scripts/maintenance/import_seed_data.py
    python scripts/maintenance/import_seed_data.py --source path/to/seed.db --dry-run
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from models import Season, Community, League, Team, Standing
from database import engine as dest_engine


def league_key(l):
    return (l.slug, l.stream, l.type)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default='data/seed/hockey_calgary.db',
                        help='Source SQLite database (default: data/seed/hockey_calgary.db)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Report what would be imported without writing.')
    args = parser.parse_args()

    src_path = Path(args.source).resolve()
    if not src_path.exists():
        print(f"Source SQLite DB not found: {src_path}")
        sys.exit(1)

    src_engine = create_engine(f"sqlite:///{src_path}")
    SrcSession = sessionmaker(bind=src_engine)
    DestSession = sessionmaker(bind=dest_engine)

    print(f"Source:      {src_path}")
    print(f"Destination: {dest_engine.url}")
    print(f"Dry run:     {args.dry_run}")
    print()

    src = SrcSession()
    dest = DestSession()

    stats = {
        'seasons_new': 0, 'communities_new': 0, 'leagues_new': 0,
        'teams_new': 0, 'teams_remapped_skipped': 0,
        'standings_new': 0, 'standings_skipped_existing': 0, 'standings_skipped_no_community': 0,
    }

    try:
        # --- Seasons ---
        dest_seasons_by_name = {s.name: s for s in dest.query(Season).all()}
        for s_src in src.query(Season).all():
            if s_src.name not in dest_seasons_by_name:
                s_new = Season(name=s_src.name)
                dest.add(s_new)
                dest_seasons_by_name[s_src.name] = s_new
                stats['seasons_new'] += 1
        dest.flush()

        # --- Communities ---
        dest_comms_by_name = {c.name: c for c in dest.query(Community).all()}
        for c_src in src.query(Community).all():
            if c_src.name not in dest_comms_by_name:
                c_new = Community(name=c_src.name)
                dest.add(c_new)
                dest_comms_by_name[c_src.name] = c_new
                stats['communities_new'] += 1
        dest.flush()

        # --- Leagues ---
        dest_leagues_by_key = {league_key(l): l for l in dest.query(League).all()}
        for l_src in src.query(League).all():
            k = league_key(l_src)
            if k not in dest_leagues_by_key:
                l_new = League(name=l_src.name, slug=l_src.slug, stream=l_src.stream, type=l_src.type)
                dest.add(l_new)
                dest_leagues_by_key[k] = l_new
                stats['leagues_new'] += 1
        dest.flush()

        # --- Teams ---
        # Live wins on community attribution: if a team already exists in dest with a
        # different community than seed, keep the live mapping (don't rewrite history).
        dest_teams_by_name = {t.name: t for t in dest.query(Team).all()}
        for t_src in src.query(Team).all():
            if t_src.name in dest_teams_by_name:
                # Already exists; do nothing (live mapping authoritative)
                dest_team = dest_teams_by_name[t_src.name]
                # Find what community the seed used
                seed_comm = src.query(Community).filter_by(id=t_src.community_id).first()
                if seed_comm and dest_team.community_id != dest_comms_by_name[seed_comm.name].id:
                    stats['teams_remapped_skipped'] += 1
                continue

            # New team — resolve seed's community_id to dest community via name
            seed_comm = src.query(Community).filter_by(id=t_src.community_id).first()
            if not seed_comm:
                continue
            dest_comm = dest_comms_by_name.get(seed_comm.name)
            if not dest_comm:
                continue
            t_new = Team(name=t_src.name, community_id=dest_comm.id)
            dest.add(t_new)
            dest_teams_by_name[t_src.name] = t_new
            stats['teams_new'] += 1
        dest.flush()

        # --- Standings ---
        # Build a lookup of existing (season_id, league_id, team_id) in dest
        existing_keys = set(
            (s.season_id, s.league_id, s.team_id)
            for s in dest.query(Standing.season_id, Standing.league_id, Standing.team_id).all()
        )

        # We need a way to map seed's (season_id, league_id, team_id) -> dest IDs.
        seed_season_by_id = {s.id: s.name for s in src.query(Season).all()}
        seed_league_by_id = {l.id: league_key(l) for l in src.query(League).all()}
        seed_team_by_id = {t.id: t.name for t in src.query(Team).all()}
        seed_comm_by_id = {c.id: c.name for c in src.query(Community).all()}

        # Read seed standings via raw SQL — the seed schema predates `community_id`,
        # so the ORM-mapped Standing model fails against it. Inspect columns first
        # so we don't assume schema we don't have.
        src_conn = src.connection()
        seed_cols = {row[1] for row in src_conn.exec_driver_sql("PRAGMA table_info(standings)").fetchall()}
        rows_seed = src_conn.exec_driver_sql(
            "SELECT season_id, league_id, team_id, gp, w, l, t, pts, gf, ga, diff, source_url FROM standings"
        ).fetchall()

        # Build a tiny record class so the loop below stays readable
        from collections import namedtuple
        SeedStanding = namedtuple('SeedStanding', 'season_id league_id team_id gp w l t pts gf ga diff source_url')
        seed_standings = [SeedStanding(*r) for r in rows_seed]
        print(f"  read {len(seed_standings)} standings from seed (columns: {sorted(seed_cols)})")

        for st_src in seed_standings:
            season_name = seed_season_by_id.get(st_src.season_id)
            l_key = seed_league_by_id.get(st_src.league_id)
            team_name = seed_team_by_id.get(st_src.team_id)
            if not (season_name and l_key and team_name):
                continue

            dest_season = dest_seasons_by_name.get(season_name)
            dest_league = dest_leagues_by_key.get(l_key)
            dest_team = dest_teams_by_name.get(team_name)
            if not (dest_season and dest_league and dest_team):
                continue

            key = (dest_season.id, dest_league.id, dest_team.id)
            if key in existing_keys:
                stats['standings_skipped_existing'] += 1
                continue

            # Resolve community_id at scrape time (denormalized snapshot).
            # Seed standings don't have community_id, but the seed's team did,
            # so use the seed-team community resolved to dest community.
            seed_team = src.query(Team).filter_by(id=st_src.team_id).first()
            comm_id = None
            if seed_team and seed_team.community_id:
                seed_comm_name = seed_comm_by_id.get(seed_team.community_id)
                if seed_comm_name and seed_comm_name in dest_comms_by_name:
                    comm_id = dest_comms_by_name[seed_comm_name].id
            if comm_id is None:
                stats['standings_skipped_no_community'] += 1
                continue

            dest.add(Standing(
                season_id=dest_season.id,
                league_id=dest_league.id,
                team_id=dest_team.id,
                community_id=comm_id,
                gp=st_src.gp, w=st_src.w, l=st_src.l, t=st_src.t,
                pts=st_src.pts, gf=st_src.gf, ga=st_src.ga, diff=st_src.diff,
                source_url=st_src.source_url,
            ))
            existing_keys.add(key)
            stats['standings_new'] += 1

        if args.dry_run:
            print("(dry-run; rolling back)")
            dest.rollback()
        else:
            dest.commit()
            print("Committed.")
    finally:
        src.close()
        dest.close()

    print()
    print("Summary:")
    for k, v in stats.items():
        print(f"  {k:<35} {v:>5}")


if __name__ == '__main__':
    main()
