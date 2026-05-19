"""
Scrape completed game results (final scores) and persist them to the `games`
table.

Three upstream sources, routed by `standings.source_url`:

- RAMP        — `http://hockeycalgary.msa4.rampinteractive.com/api/leaguegame/get/...`
                covers U11 (2024-2025 onward).
- TeamLinkt   — `https://leagues.teamlinkt.com/leagues/getAllEvents/{assoc}`
                covers U13 (2025-2026 onward).
- hockeycalgary.ca — `/schedule/scores/league/{slug}/season/{season}` HTML page
                covers U13 (2024-2025) and U15 (2024-2025 onward).

Scope: only U11/U13/U15 leagues with a season >= 2024-2025, and only games
flagged as completed by the source.
"""
from __future__ import annotations

import re
import json
from datetime import datetime
from collections import defaultdict
from typing import Iterable

from bs4 import BeautifulSoup
from sqlalchemy.exc import IntegrityError

from database import SessionLocal
from models import Season, League, Team, Standing, Game
from scraper import SESSION, HTTP_TIMEOUT, get_soup
from utilities.utils import normalize_team_name


MIN_SEASON_NAME = "2024-2025"
ALLOWED_AGES = ("U11", "U13", "U15")

# ------------------------------------------------------------------ helpers --

def _season_year_start(name: str) -> int:
    """'2024-2025' -> 2024. Used to filter to seasons >= MIN_SEASON_NAME."""
    m = re.match(r"(\d{4})", name or "")
    return int(m.group(1)) if m else 0


def _league_age(league_name: str) -> str | None:
    m = re.search(r"U\d{1,2}", league_name or "")
    return m.group(0) if m else None


def _strip_score_suffix(team_name: str) -> str:
    """TeamLinkt embeds the score as a trailing ' (N)'. Drop it for matching."""
    return re.sub(r"\s*\(\d+\)\s*$", "", (team_name or "")).strip()


def _strip_html(text: str) -> str:
    if not text:
        return ""
    return BeautifulSoup(text, "html.parser").get_text(strip=True)


# ----------------------------------------------------------------- RAMP -----

# RAMP standings source_url:
#   /api/leaguegame/getstandings3cached/{assoc}/{sid}/{gtid}/{cat}/{did}/0/0
_RAMP_RE = re.compile(
    r"rampinteractive\.com/api/leaguegame/getstandings3cached/(\d+)/(\d+)/(\d+)/(\d+)/(\d+)/"
)


def parse_ramp_source_url(url: str) -> dict | None:
    m = _RAMP_RE.search(url or "")
    if not m:
        return None
    assoc, sid, gtid, cat, did = m.groups()
    return {"assoc": assoc, "sid": sid, "gtid": gtid, "cat": cat, "did": did}


def fetch_ramp_games(assoc: str, sid: str, gtid: str, cat: str, did: str) -> list[dict]:
    """Iterate every month in the season and concat games. Only completed."""
    months_url = (
        f"http://hockeycalgary.msa4.rampinteractive.com/api/leaguegame/"
        f"getMonthYears/{assoc}/{sid}/{gtid}/{did}/0"
    )
    try:
        resp = SESSION.get(months_url, timeout=HTTP_TIMEOUT)
        months = resp.json() if resp.status_code == 200 else []
    except Exception as e:
        print(f"  RAMP getMonthYears failed: {e}")
        return []

    games: list[dict] = []
    for m in months or []:
        my = m.get("Value")  # e.g. "10,2025"
        if not my:
            continue
        api = (
            f"http://hockeycalgary.msa4.rampinteractive.com/api/leaguegame/"
            f"get/{assoc}/{sid}/{cat}/{did}/{gtid}/0/{my}"
        )
        try:
            resp = SESSION.get(api, timeout=HTTP_TIMEOUT)
            data = resp.json() if resp.status_code == 200 else []
        except Exception:
            continue
        for g in data or []:
            if not g.get("completed"):
                continue
            if g.get("cancelledHome") or g.get("cancelledAway") or g.get("rainout") or g.get("trash"):
                continue
            try:
                home = _strip_score_suffix(g.get("HomeTeamName") or "")
                away = _strip_score_suffix(g.get("AwayTeamName") or "")
                hs = int(g.get("homeScore"))
                as_ = int(g.get("awayScore"))
            except (TypeError, ValueError):
                continue
            if not home or not away:
                continue
            played = g.get("sDate")
            try:
                played_at = datetime.fromisoformat(played) if played else None
            except ValueError:
                played_at = None
            games.append({
                "source": "RAMP",
                "source_game_id": str(g.get("GID")),
                "home_team": normalize_team_name(home),
                "away_team": normalize_team_name(away),
                "home_score": hs,
                "away_score": as_,
                "played_at": played_at,
                "venue": g.get("ArenaName"),
                "game_type": g.get("GameTypeName") or "Regular",
                "source_url": f"http://hockeycalgary.msa4.rampinteractive.com/game/{g.get('GID')}",
            })
    return games


# ------------------------------------------------------------ hockeycalgary --

# HC standings source_url:
#   /standings/index/stream/{stream}/league/{slug}/season/{season}/type/{type}
_HC_RE = re.compile(
    r"hockeycalgary\.ca/standings/index/stream/([^/]+)/league/([^/]+)/season/([^/]+)/type/"
)


def parse_hc_source_url(url: str) -> dict | None:
    m = _HC_RE.search(url or "")
    if not m:
        return None
    stream, slug, season = m.groups()
    return {"stream": stream, "slug": slug, "season": season}


# Mapping from HC's Type column on the scores page to our leagues.type enum.
_HC_TYPE_MAP = {
    "League": "Regular",
    "Regular": "Regular",
    "Seeding": "Seeding",
    "Playoff": "Playoff",
    "Playoffs": "Playoff",
    "Tournament": "Tournament",
}


def fetch_hc_games(slug: str, season: str) -> list[dict]:
    """Parses /schedule/scores/league/{slug}/season/{season}."""
    url = f"https://www.hockeycalgary.ca/schedule/scores/league/{slug}/season/{season}"
    soup = get_soup(url)
    if not soup:
        return []

    table = soup.find("table", class_="games-table")
    if not table:
        return []

    rows = table.find_all("tr")
    if len(rows) < 2:
        return []

    games: list[dict] = []
    for tr in rows[1:]:
        tds = tr.find_all("td")
        if len(tds) < 9:
            continue
        try:
            date_str = tds[0].get_text(strip=True)
            time_str = tds[1].get_text(strip=True)
            arena = tds[2].get_text(strip=True)
            home_text = tds[4].get_text(strip=True)
            score_text = tds[5].get_text(strip=True)
            away_text = tds[6].get_text(strip=True)
            type_text = tds[7].get_text(strip=True)
            game_no = tds[8].get_text(strip=True)
        except Exception:
            continue

        # "4 - 7" or sometimes "4 - 7 OT" / "TBD"
        m = re.match(r"\s*(\d+)\s*-\s*(\d+)", score_text)
        if not m:
            continue
        hs, as_ = int(m.group(1)), int(m.group(2))

        # Strip the "- N" suffix the markup appends to mobile-score spans.
        home = re.sub(r"\s*-\s*\d+\s*$", "", home_text).strip()
        away = re.sub(r"\s*-\s*\d+\s*$", "", away_text).strip()
        if not home or not away or not game_no:
            continue

        # Parse played_at — date is YYYY-MM-DD, time looks like "7:30pm to 8:45pm".
        played_at = None
        start_m = re.match(r"(\d{1,2}:\d{2}\s*[apAP][mM])", time_str or "")
        try:
            if start_m:
                played_at = datetime.strptime(
                    f"{date_str} {start_m.group(1).upper()}",
                    "%Y-%m-%d %I:%M%p",
                )
            else:
                played_at = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            played_at = None

        games.append({
            "source": "hockeycalgary",
            # HC's Game # is unique per season-league combination but not globally.
            # Prefix with slug+season to keep the (source, source_game_id) unique key safe.
            "source_game_id": f"{slug}|{season}|{game_no}",
            "home_team": normalize_team_name(home),
            "away_team": normalize_team_name(away),
            "home_score": hs,
            "away_score": as_,
            "played_at": played_at,
            "venue": arena,
            "game_type": _HC_TYPE_MAP.get(type_text, "Regular"),
            "source_url": url,
        })
    return games


# --------------------------------------------------------------- TeamLinkt --

# TeamLinkt standings source_url:
#   /leagues/getStandings/{assoc}/{season_id}
_TL_RE = re.compile(r"leagues\.teamlinkt\.com/leagues/getStandings/(\d+)/(\d+)")


def parse_teamlinkt_source_url(url: str) -> dict | None:
    m = _TL_RE.search(url or "")
    if not m:
        return None
    assoc, season_id = m.groups()
    return {"assoc": assoc, "season_id": season_id}


def fetch_teamlinkt_games(assoc: str, season_id: str) -> list[dict]:
    """
    TeamLinkt returns one big event-list per (assoc, season_id). Their datatable
    filter on hierarchy is broken (server ignores group_ids), so we pull all
    events at once and let `sync_games` attribute each to a league by
    matching team names against our standings table.
    """
    url = f"https://leagues.teamlinkt.com/leagues/getAllEvents/{assoc}"
    try:
        resp = SESSION.post(
            url,
            data={"season_id": season_id},
            headers={"X-Requested-With": "XMLHttpRequest"},
            timeout=HTTP_TIMEOUT,
        )
        data = resp.json()
        if isinstance(data, str):
            data = json.loads(data)
    except Exception as e:
        print(f"  TeamLinkt getAllEvents failed: {e}")
        return []

    rows = data.get("data") if isinstance(data, dict) else None
    if not rows:
        return []

    games: list[dict] = []
    for r in rows:
        # Only rows whose third column starts with "Game" are scheduled matches;
        # the same datatable lists practices, tryouts, etc. as other event types.
        kind = _strip_html(r.get("2", ""))
        if not kind.lower().startswith("game"):
            continue

        date_str = (r.get("0") or "").strip()
        time_str = (r.get("1") or "").strip()
        home_raw = r.get("3") or ""
        away_raw = r.get("4") or ""
        venue = _strip_html(r.get("5") or "")
        ts = r.get("6")

        # Score is embedded in the team-name HTML as a trailing "(N)" span.
        def split_team_score(blob: str) -> tuple[str, int | None]:
            text = _strip_html(blob)
            m = re.match(r"^(.*?)\s*\((\d+)\)\s*$", text)
            if not m:
                return text.strip(), None
            return m.group(1).strip(), int(m.group(2))

        home_team, hs = split_team_score(home_raw)
        away_team, as_ = split_team_score(away_raw)
        # Completed only — both scores must be present and non-null.
        if hs is None or as_ is None:
            continue
        if not home_team or not away_team:
            continue

        # Source game id lives in the event-link href: .../event/{assoc}/{gid}
        gid_m = re.search(r"/event/\d+/(\d+)", r.get("2", ""))
        if not gid_m:
            continue
        gid = gid_m.group(1)

        played_at = None
        if ts:
            try:
                played_at = datetime.fromtimestamp(int(ts))
            except (TypeError, ValueError):
                pass
        if played_at is None and date_str:
            # Fallback "Sat Oct 18, 2025"
            try:
                played_at = datetime.strptime(date_str, "%a %b %d, %Y")
            except ValueError:
                pass

        games.append({
            "source": "TeamLinkt",
            "source_game_id": gid,
            "home_team": normalize_team_name(home_team),
            "away_team": normalize_team_name(away_team),
            "home_score": hs,
            "away_score": as_,
            "played_at": played_at,
            "venue": venue or None,
            "game_type": "Regular",
            "source_url": f"https://leagues.teamlinkt.com/Leagues/event/{assoc}/{gid}",
        })
    return games


# ---------------------------------------------------- persistence + routing --

def _build_team_league_map(db, season_ids: list[int]) -> dict:
    """
    For each (season_id, team_name), figure out the team's PRIMARY league_id
    (the one with the most games played in standings). Used to route games to
    leagues when the upstream feed doesn't carry the league explicitly.
    """
    if not season_ids:
        return {}

    rows = (
        db.query(
            Standing.season_id,
            Standing.team_id,
            Standing.league_id,
            Team.name,
            League.type,
            Standing.gp,
        )
        .join(Team, Team.id == Standing.team_id)
        .join(League, League.id == Standing.league_id)
        .filter(Standing.season_id.in_(season_ids))
        .all()
    )

    # (season_id, team_name) -> {(league_id, type): gp}
    grouped: dict[tuple[int, str], dict[tuple[int, str], int]] = defaultdict(dict)
    for season_id, team_id, league_id, name, ltype, gp in rows:
        key = (season_id, name)
        grouped[key][(league_id, ltype or "Regular")] = gp or 0

    return grouped


def _resolve_league(
    team_league_map: dict,
    season_id: int,
    home_team: str,
    away_team: str,
    game_type: str,
) -> int | None:
    """
    Pick the league_id for a game. Strategy:
      1. Find the set of league_ids that both teams are in for this season.
      2. Prefer leagues whose `type` matches the game_type (e.g. Seeding game
         routes to a Seeding league when one exists).
      3. Among the remainder, pick the league where each team played the most
         standings games — handles the common Regular case.
    Returns None if there is no league both teams played in.
    """
    home_options = team_league_map.get((season_id, home_team), {})
    away_options = team_league_map.get((season_id, away_team), {})
    if not home_options or not away_options:
        return None

    home_leagues = {lid for (lid, _t) in home_options.keys()}
    away_leagues = {lid for (lid, _t) in away_options.keys()}
    shared = home_leagues & away_leagues
    if not shared:
        return None

    # Score each candidate by (type-match-bonus, combined gp).
    def score(lid: int) -> tuple[int, int]:
        type_match = 0
        gp_total = 0
        for (xlid, t), gp in home_options.items():
            if xlid == lid:
                type_match += 1 if (t == game_type) else 0
                gp_total += gp
        for (xlid, t), gp in away_options.items():
            if xlid == lid:
                type_match += 1 if (t == game_type) else 0
                gp_total += gp
        return (type_match, gp_total)

    return max(shared, key=score)


def _save_games_for_source(db, source: str, games: list[dict], team_league_map: dict, season_id: int, default_league_id: int | None = None):
    """
    Persist a batch of games. Resolves home/away to team_id and to league_id
    (either passed in, or resolved via team_league_map).

    Uses Postgres INSERT ... ON CONFLICT DO UPDATE on the (source, source_game_id)
    unique constraint so re-runs are idempotent and concurrent batches don't blow
    up on duplicates.
    """
    if not games:
        return 0, 0, 0

    # Dedupe in-batch by source_game_id (last write wins). Upstream feeds
    # occasionally return the same game in adjacent month buckets at boundaries.
    by_sid: dict[str, dict] = {}
    for g in games:
        by_sid[g["source_game_id"]] = g
    games = list(by_sid.values())

    # Preload team rows we need.
    needed_names = set()
    for g in games:
        needed_names.add(g["home_team"])
        needed_names.add(g["away_team"])
    teams_by_name = {
        t.name: t for t in db.query(Team).filter(Team.name.in_(needed_names)).all()
    }

    rows_to_upsert: list[dict] = []
    skipped = 0
    for g in games:
        home = teams_by_name.get(g["home_team"])
        away = teams_by_name.get(g["away_team"])
        if not home or not away:
            skipped += 1
            continue

        if default_league_id is not None:
            league_id = default_league_id
        else:
            league_id = _resolve_league(
                team_league_map, season_id, g["home_team"], g["away_team"], g.get("game_type") or "Regular",
            )
        if league_id is None:
            skipped += 1
            continue

        rows_to_upsert.append({
            "season_id": season_id,
            "league_id": league_id,
            "home_team_id": home.id,
            "away_team_id": away.id,
            "home_score": g["home_score"],
            "away_score": g["away_score"],
            "played_at": g.get("played_at"),
            "venue": g.get("venue"),
            "game_type": g.get("game_type") or "Regular",
            "source": source,
            "source_game_id": g["source_game_id"],
            "source_url": g.get("source_url"),
        })

    if not rows_to_upsert:
        return 0, 0, skipped

    from sqlalchemy.dialects.postgresql import insert as pg_insert
    stmt = pg_insert(Game.__table__).values(rows_to_upsert)
    update_cols = {
        col.name: stmt.excluded[col.name]
        for col in Game.__table__.columns
        if col.name not in ("id", "source", "source_game_id")
    }
    stmt = stmt.on_conflict_do_update(
        constraint="_game_source_uc",
        set_=update_cols,
    )
    db.execute(stmt)
    db.commit()
    # We don't get a precise inserted/updated split out of ON CONFLICT, so
    # report rows_to_upsert as the "touched" count and leave updated=0.
    return len(rows_to_upsert), 0, skipped


# ------------------------------------------------------- top-level orchestrator

def _eligible_standings(db) -> list[tuple]:
    """
    Return (season_id, season_name, league_id, league_name, league_slug,
            league_stream, league_type, source_url) for every standings row
    where age in {U11,U13,U15} and season >= 2024-2025.

    Distinct on (season_id, league_id) — same league has many team rows.
    """
    rows = (
        db.query(
            Season.id,
            Season.name,
            League.id,
            League.name,
            League.slug,
            League.stream,
            League.type,
            Standing.source_url,
        )
        .join(Season, Season.id == Standing.season_id)
        .join(League, League.id == Standing.league_id)
        .all()
    )
    out = []
    seen = set()
    for sid, sname, lid, lname, lslug, lstream, ltype, surl in rows:
        if _season_year_start(sname) < _season_year_start(MIN_SEASON_NAME):
            continue
        age = _league_age(lname)
        if age not in ALLOWED_AGES:
            continue
        if (sid, lid) in seen:
            continue
        seen.add((sid, lid))
        out.append((sid, sname, lid, lname, lslug, lstream, ltype, surl))
    return out


def sync_games(progress_callback=None) -> dict:
    """
    Walk every eligible (season, league) standings group, route to the right
    fetcher by source_url, and persist games. Returns a small stats dict.

    Attribution strategy:
      - RAMP: source_url carries did+gtid → games are unambiguously scoped to
        one league row → pass default_league_id.
      - HC: source_url scopes by (slug, season) but the scores page mixes
        Regular / Seeding / Playoff. Look up the right league_id per game by
        (slug, season, mapped game_type).
      - TeamLinkt: feed has no per-game league info. Fall back to the
        team-league resolver — but restrict the map to U11/U13/U15 so that
        teams which also play U18 don't drag games into the wrong league.
    """
    db = SessionLocal()
    stats = {"leagues": 0, "inserted": 0, "updated": 0, "skipped": 0, "no_route": 0}
    try:
        groups = _eligible_standings(db)
        total = len(groups)
        if total == 0:
            return stats

        teamlinkt_groups: dict[tuple[str, str], list[tuple]] = defaultdict(list)
        ramp_groups: list[tuple] = []
        hc_groups: list[tuple] = []

        # For HC, build (slug, season, mapped_type) -> league_id from the
        # standings rows we're already iterating.
        hc_league_index: dict[tuple[str, str, str], int] = {}

        for g in groups:
            sid, sname, lid, lname, lslug, lstream, ltype, surl = g
            tl = parse_teamlinkt_source_url(surl)
            ramp = parse_ramp_source_url(surl)
            hc = parse_hc_source_url(surl)
            if tl:
                teamlinkt_groups[(tl["assoc"], tl["season_id"])].append(g)
            elif ramp:
                ramp_groups.append(g)
            elif hc:
                hc_groups.append(g)
                hc_league_index[(hc["slug"], hc["season"], (ltype or "Regular"))] = lid
            else:
                stats["no_route"] += 1

        # Team-league map: keyed by season — restricted to leagues we're
        # actually scraping for games (U11/U13/U15), so a team that plays
        # both U15 and U18 in the same season doesn't accidentally pull U15
        # games into a U18 row.
        season_ids = sorted({g[0] for g in groups})
        team_league_map = _build_team_league_map(db, season_ids)

        done = 0

        # ---- RAMP: one fetch per league (gtid+did scopes it precisely). -----
        for g in ramp_groups:
            sid, sname, lid, lname, lslug, lstream, ltype, surl = g
            rp = parse_ramp_source_url(surl)
            if not rp:
                continue
            print(f"  [RAMP] {sname} {lname}...")
            games = fetch_ramp_games(**rp)
            i, u, s = _save_games_for_source(
                db, "RAMP", games, team_league_map, sid, default_league_id=lid,
            )
            stats["inserted"] += i; stats["updated"] += u; stats["skipped"] += s; stats["leagues"] += 1
            done += 1
            if progress_callback:
                progress_callback(int(done * 100 / total), f"games: {done}/{total}")

        # ---- TeamLinkt: one fetch per (assoc, season_id) — covers all leagues
        # for that season in a single events call. Dedup the (assoc, season_id)
        # key first so we don't fetch the same payload twice when the same
        # season has both Regular and Seeding TeamLinkt league rows.
        for (assoc, season_id), groups_in_season in teamlinkt_groups.items():
            sid = groups_in_season[0][0]
            sname = groups_in_season[0][1]
            print(f"  [TeamLinkt] {sname} ({len(groups_in_season)} leagues, single events fetch)...")
            games = fetch_teamlinkt_games(assoc, season_id)
            i, u, s = _save_games_for_source(
                db, "TeamLinkt", games, team_league_map, sid, default_league_id=None,
            )
            stats["inserted"] += i; stats["updated"] += u; stats["skipped"] += s; stats["leagues"] += len(groups_in_season)
            done += len(groups_in_season)
            if progress_callback:
                progress_callback(int(done * 100 / total), f"games: {done}/{total}")

        # ---- HC: one fetch per (slug, season) — page mixes all game types. ---
        seen_hc = set()
        for g in hc_groups:
            sid, sname, lid, lname, lslug, lstream, ltype, surl = g
            hp = parse_hc_source_url(surl)
            if not hp:
                continue
            key = (hp["slug"], hp["season"])
            if key in seen_hc:
                done += 1
                continue
            seen_hc.add(key)

            print(f"  [HC] {sname} {lname}...")
            games = fetch_hc_games(hp["slug"], hp["season"])

            # Bucket games by mapped league_id (per game_type → our league.type).
            by_league: dict[int, list[dict]] = defaultdict(list)
            unmapped = 0
            for game in games:
                target_lid = hc_league_index.get(
                    (hp["slug"], hp["season"], game.get("game_type") or "Regular")
                )
                if target_lid is None:
                    unmapped += 1
                    continue
                by_league[target_lid].append(game)

            for target_lid, batch in by_league.items():
                i, u, s = _save_games_for_source(
                    db, "hockeycalgary", batch, team_league_map, sid, default_league_id=target_lid,
                )
                stats["inserted"] += i; stats["updated"] += u; stats["skipped"] += s
            stats["skipped"] += unmapped
            stats["leagues"] += 1
            done += 1
            if progress_callback:
                progress_callback(int(done * 100 / total), f"games: {done}/{total}")
    finally:
        db.close()

    return stats


if __name__ == "__main__":
    s = sync_games()
    print("Done:", s)
