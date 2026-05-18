import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import time
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from database import init_db, SessionLocal, engine
from models import Season, League, Team, Community, Standing, ScrapeRun, Base
from utilities.utils import normalize_community_name, load_community_map, save_community_map
import urllib3
from collections import defaultdict
import re
import json

import concurrent.futures
import threading

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://www.hockeycalgary.ca"

# Current season — used as a fallback when discovery fails. Update once a year.
CURRENT_SEASON = "2025-2026"

# Historical seasons fetched in addition to the current one. Used by both the
# top-level _do_sync discovery loop and by process_league as a fallback when a
# league page doesn't render a server-side season selector (e.g. elite-council).
HISTORICAL_YEARS = ["2024-2025", "2023-2024", "2022-2023", "2021-2022", "2020-2021"]

# Request timeouts in seconds: (connect, read)
HTTP_TIMEOUT = (5, 30)


def _build_session():
    """Module-level HTTP session: connection pooling, retries, sensible defaults."""
    s = requests.Session()
    s.verify = False
    s.headers.update({
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/124.0 Safari/537.36'
        )
    })
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(['GET', 'POST']),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=32, pool_maxsize=32)
    s.mount('http://', adapter)
    s.mount('https://', adapter)
    return s


SESSION = _build_session()


def get_soup(url):
    try:
        response = SESSION.get(url, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    except requests.Timeout:
        print(f"Timeout fetching {url}")
        return None
    except requests.HTTPError as e:
        print(f"HTTP {e.response.status_code} fetching {url}")
        return None
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


def get_or_create(db, model, defaults=None, **filters):
    """
    Fetch a row matching `filters` or create one with `filters` + `defaults`.
    Safe under concurrent threads: if a parallel worker inserts the same row
    between our query and insert, we catch IntegrityError and re-query.

    Always releases the implicit read-transaction before returning so callers
    that follow with long non-DB work (e.g. HTTP fetches) don't pin a Postgres
    transaction open. Returns (instance, created_bool).
    """
    instance = db.query(model).filter_by(**filters).first()
    if instance is not None:
        # Release the read transaction so the session doesn't sit idle-in-transaction.
        db.commit()
        return instance, False

    params = dict(filters)
    if defaults:
        params.update(defaults)
    instance = model(**params)
    db.add(instance)
    try:
        db.commit()
        return instance, True
    except IntegrityError:
        db.rollback()
        instance = db.query(model).filter_by(**filters).first()
        db.commit()
        return instance, False

def get_leagues(year=None):
    # The bare /standings page no longer lists league links — only the season-scoped
    # /standings/index/season/<year> does. Default to CURRENT_SEASON when no year given.
    season_for_url = year or CURRENT_SEASON
    url = f"{BASE_URL}/standings/index/season/{season_for_url}"

    soup = get_soup(url)
    if not soup:
        return []

    leagues = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/standings/index/stream/' in href and '/league/' in href:
            parts = href.split('/')
            try:
                stream_idx = parts.index('stream') + 1
                league_idx = parts.index('league') + 1
                stream = parts[stream_idx]
                slug = parts[league_idx]
                name = a.get_text(strip=True)
                
                # Determine type based on name
                league_type = 'Regular'
                if 'Seeding' in name:
                    league_type = 'Seeding'
                elif 'Playoff' in name:
                    league_type = 'Playoff'
                
                # Filter for U13, U15, U16, U18. U11 is intentionally excluded —
                # the legacy hockeycalgary.ca site publishes empty U11 standings tables
                # (U11 data lives on RAMP / Alberta One). U9 has no published standings.
                if any(cat in name for cat in ['U13', 'U15', 'U16', 'U18']):
                    leagues.append({
                        'name': name,
                        'slug': slug,
                        'stream': stream,
                        'url': f"{BASE_URL}{href}",
                        'type': league_type
                    })
            except (ValueError, IndexError):
                continue
    if not leagues:
        print(f"  WARN: get_leagues({season_for_url}) returned 0 leagues — URL pattern may have changed.")
    return leagues

def get_ramp_leagues():
    """
    Scrapes U11 leagues from the RAMP Interactive site.
    """
    url = "http://hockeycalgary.msa4.rampinteractive.com/"
    soup = get_soup(url)
    if not soup:
        return []
        
    leagues = []
    standings_links = soup.find_all('a', string=lambda t: t and 'Standings' in t)
    
    for a in standings_links:
        href = a['href']
        # Traverse up to find a header for the league name
        parent = a.parent
        found_name = None
        
        # Go up 5 levels max
        curr = parent
        for _ in range(5):
            if not curr: break
            
            # Check previous siblings for headers
            prev = curr.find_previous_sibling(['h1', 'h2', 'h3', 'h4', 'h5', 'div'])
            if prev:
                text = prev.get_text(strip=True)
                if text and len(text) < 50 and 'Games' not in text:
                    found_name = text
                    break
            
            header = curr.find(['h1', 'h2', 'h3', 'h4', 'h5'])
            if header:
                 text = header.get_text(strip=True)
                 if text:
                     found_name = text
                     break
                     
            curr = curr.parent
            
        if found_name:
            # href is like /division/3300/30084/standings
            # slug can be 3300/30084
            try:
                slug = href.replace('/division/', '').replace('/standings', '')
                leagues.append({
                    'name': found_name,
                    'slug': slug,
                    'stream': 'RAMP',
                    'url': f"http://hockeycalgary.msa4.rampinteractive.com{href}",
                    'type': 'Regular' # Assume regular for now
                })
            except Exception:
                continue
                
    return leagues

def get_teamlinkt_leagues():
    """
    Scrapes U13+ leagues from TeamLinkt.

    TeamLinkt's hierarchy_filter dropdown sometimes lists the *same* league
    under multiple "association" hierarchies — e.g. both `260972-260985` and
    `249020-249139` for U13 Tier 5 South. Each option points at a different
    upstream API endpoint, but they return effectively the same standings.
    Treating them as distinct leagues produces duplicate `leagues` rows and
    inflates downstream `standings` counts.

    Dedupe by display name; when two options share a name, prefer the one
    with the higher numeric slug prefix (the newer hierarchy ID — TeamLinkt
    appears to mint these monotonically, and empirically the higher prefix
    is the one that contains real data; the lower prefix is often an empty
    legacy stub).
    """
    url = "https://leagues.teamlinkt.com/hockeycalgary/Standings"
    soup = get_soup(url)
    if not soup:
        return []

    select = soup.find('select', {'name': 'hierarchy_filter'}) or soup.find('select', {'id': 'hierarchy_filter'})
    if not select:
        return []

    # First pass: collect raw options, attach the slug prefix for comparison.
    raw = []
    for opt in select.find_all('option'):
        name = opt.get_text(strip=True)
        value = opt.get('value')
        if not value or value == '0':
            continue
        # Exclude U15 from TeamLinkt as it is sourced from Community Council
        if 'U15' in name:
            continue
        try:
            prefix = int((value.split('-', 1)[0] or '0'))
        except ValueError:
            prefix = 0
        raw.append({'name': name, 'slug': value, 'prefix': prefix})

    # Second pass: dedupe by name, keep the entry with the highest prefix.
    by_name = {}
    for r in raw:
        existing = by_name.get(r['name'])
        if existing is None or r['prefix'] > existing['prefix']:
            by_name[r['name']] = r

    dropped = len(raw) - len(by_name)
    if dropped:
        print(f"  TeamLinkt: dropped {dropped} duplicate league option(s); kept higher-prefix slugs")

    return [
        {
            'name': r['name'],
            'slug': r['slug'],
            'stream': 'TeamLinkt',
            'url': f"{url}?hierarchy_filter={r['slug']}",
            'type': 'Regular',
        }
        for r in by_name.values()
    ]

def get_tournaments(season_slug):
    tournaments = [
        {'name': 'City Championships', 'slug': 'city-championships', 'type': 'Playoff'},
        {'name': 'Esso Minor Hockey Week', 'slug': 'esso-minor-hockey-week', 'type': 'Tournament'}
    ]
    
    results = []
    for t in tournaments:
        url = f"{BASE_URL}/tournament/content/season/{season_slug}/tournament/{t['slug']}/page/home"
        soup = get_soup(url)
        if not soup:
            continue
            
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/league/' in href and '/category/' in href:
                try:
                    league_slug = href.split('/league/')[-1]
                    name = a.get_text(strip=True)
                    
                    if any(cat in name for cat in ['U11', 'U13', 'U15', 'U16', 'U18']):
                         results.append({
                            'name': f"{t['name']} - {name}",
                            'slug': league_slug,
                            'stream': 'tournament',
                            'url': f"{BASE_URL}{href}",
                            'type': t['type']
                        })
                except IndexError:
                    continue
    return results

def get_seasons_for_league(league_url):
    soup = get_soup(league_url)
    if not soup:
        return []
    
    seasons = []
    options = soup.find_all('option')
    for option in options:
        value = option.get('value')
        text = option.get_text(strip=True)
        if value and '/season/' in value:
            season_slug = value.split('/season/')[-1]
            # Normalize season name (e.g. 2025/2026 -> 2025-2026)
            normalized_name = text.replace('/', '-')
            seasons.append({
                'name': normalized_name,
                'slug': season_slug,
                'url': f"{BASE_URL}{value}"
            })
    return seasons

def parse_standings(soup):
    standings_data = []
    table = soup.find('table', class_='table')
    
    tables = soup.find_all('table')
    target_table = None
    for t in tables:
        headers = [th.get_text(strip=True) for th in t.find_all('th')]
        if ('GP' in headers or 'Games played' in headers) and ('PTS' in headers or 'points' in headers):
            target_table = t
            break
            
    if not target_table:
        return []
        
    rows = target_table.find_all('tr')
    headers = [th.get_text(strip=True) for th in rows[0].find_all('th')]
    
    header_map = {
        'Team': 'team',
        'GP': 'gp', 'Games played': 'gp',
        'W': 'w', 'Wins': 'w',
        'L': 'l', 'losses': 'l', 'Losses': 'l',
        'T': 't', 'ties': 't', 'Ties': 't',
        'PTS': 'pts', 'points': 'pts', 'Points': 'pts',
        'GF': 'gf', 'goals for': 'gf', 'Goals For': 'gf',
        'GA': 'ga', 'goals against': 'ga', 'Goals Against': 'ga',
        'Diff': 'diff', 'DIFF': 'diff', 'Goal Differential': 'diff'
    }
    
    col_indices = {}
    for idx, h in enumerate(headers):
        h_clean = h.strip()
        if h_clean in header_map:
            col_indices[header_map[h_clean]] = idx
        elif h_clean.lower() in header_map:
             col_indices[header_map[h_clean.lower()]] = idx
            
    if 'team' not in col_indices:
        return []
        
    for row in rows[1:]:
        cols = row.find_all('td')
        if not cols: continue
        if len(cols) == 1 and "no standings available" in cols[0].get_text(): continue
        if len(cols) < 3: continue
            
        entry = {}
        try:
            entry['team'] = cols[col_indices['team']].get_text(strip=True)
            entry['gp'] = int(cols[col_indices['gp']].get_text(strip=True) or 0)
            entry['w'] = int(cols[col_indices['w']].get_text(strip=True) or 0)
            entry['l'] = int(cols[col_indices['l']].get_text(strip=True) or 0)
            entry['t'] = int(cols[col_indices.get('t', -1)].get_text(strip=True) or 0) if 't' in col_indices else 0
            entry['pts'] = int(cols[col_indices['pts']].get_text(strip=True) or 0)
            entry['gf'] = int(cols[col_indices.get('gf', -1)].get_text(strip=True) or 0) if 'gf' in col_indices else 0
            entry['ga'] = int(cols[col_indices.get('ga', -1)].get_text(strip=True) or 0) if 'ga' in col_indices else 0
            
            if 'diff' in col_indices:
                entry['diff'] = int(cols[col_indices['diff']].get_text(strip=True) or 0)
            else:
                entry['diff'] = entry['gf'] - entry['ga']
            
            standings_data.append(entry)
        except (ValueError, IndexError):
            continue
            
    return standings_data

def parse_brackets(soup):
    standings_dict = defaultdict(lambda: {'gp': 0, 'w': 0, 'l': 0, 't': 0, 'pts': 0, 'gf': 0, 'ga': 0, 'diff': 0})
    
    game_boxes = soup.find_all('div', class_='game-box')
    
    for box in game_boxes:
        try:
            home_row = box.find('div', class_='home-row')
            visitor_row = box.find('div', class_='visitor-row')
            
            if not home_row or not visitor_row:
                continue
                
            home_team_elem = home_row.find('span', class_='team')
            visitor_team_elem = visitor_row.find('span', class_='team')
            
            if not home_team_elem or not visitor_team_elem:
                continue
                
            home_team = home_team_elem.get_text(strip=True)
            visitor_team = visitor_team_elem.get_text(strip=True)
            
            # Skip placeholders like "Winner of Game #1" if they are not actual team names
            if home_team_elem.find('a'):
                home_team = home_team_elem.find('a').get_text(strip=True)
            if visitor_team_elem.find('a'):
                visitor_team = visitor_team_elem.find('a').get_text(strip=True)
                
            if "Winner of" in home_team or "Loser of" in home_team: continue
            if "Winner of" in visitor_team or "Loser of" in visitor_team: continue
            
            home_score_span = home_row.find('span', class_='score')
            visitor_score_span = visitor_row.find('span', class_='score')
            
            if not home_score_span or not visitor_score_span:
                continue

            home_score_text = home_score_span.get_text(strip=True)
            visitor_score_text = visitor_score_span.get_text(strip=True)
            
            if not home_score_text.isdigit() or not visitor_score_text.isdigit():
                continue
                
            h_score = int(home_score_text)
            v_score = int(visitor_score_text)
            
            # Update Home Stats
            standings_dict[home_team]['gp'] += 1
            standings_dict[home_team]['gf'] += h_score
            standings_dict[home_team]['ga'] += v_score
            standings_dict[home_team]['diff'] += (h_score - v_score)
            
            # Update Visitor Stats
            standings_dict[visitor_team]['gp'] += 1
            standings_dict[visitor_team]['gf'] += v_score
            standings_dict[visitor_team]['ga'] += h_score
            standings_dict[visitor_team]['diff'] += (v_score - h_score)
            
            if h_score > v_score:
                standings_dict[home_team]['w'] += 1
                standings_dict[home_team]['pts'] += 2
                standings_dict[visitor_team]['l'] += 1
            elif v_score > h_score:
                standings_dict[visitor_team]['w'] += 1
                standings_dict[visitor_team]['pts'] += 2
                standings_dict[home_team]['l'] += 1
            else:
                standings_dict[home_team]['t'] += 1
                standings_dict[home_team]['pts'] += 1
                standings_dict[visitor_team]['t'] += 1
                standings_dict[visitor_team]['pts'] += 1
                
        except Exception as e:
            continue
            
    # Convert to list
    results = []
    for team, stats in standings_dict.items():
        stats['team'] = team
        results.append(stats)
        
    return results

def fetch_ramp_data(league_url, game_type_id=0, season_id=None, soup=None):
    # Caller can pass an already-fetched soup to avoid re-downloading the league page.
    if soup is None:
        soup = get_soup(league_url)
    if not soup: return [], None

    # Extract SID
    if season_id:
        sid = season_id
    else:
        sid_select = soup.find('select', id='ddlSeason')
        if not sid_select: return [], None
        try:
            sid = sid_select.find('option', selected=True)['value']
        except TypeError:
            # Fallback if no option is explicitly selected (use first)
            options = sid_select.find_all('option')
            if options:
                sid = options[0]['value']
            else:
                return [], None
    
    # Extract DID from URL
    # URL: .../division/3300/30078/standings
    parts = league_url.split('/')
    try:
        if 'division' in parts:
            did_idx = parts.index('division') + 2
            did = parts[did_idx]
            cat_id = parts[did_idx-1] # 3300
        else:
            return [], None
    except:
        return [], None
        
    # Search for "getstandings3cached" in scripts to find the base URL pattern
    script_content = ""
    for s in soup.find_all('script'):
        if s.string and 'getstandings3cached' in s.string:
            script_content = s.string
            break
            
    assoc_id = "3741" # Default
    if script_content:
        match = re.search(r"getstandings3cached/(\d+)/", script_content)
        if match:
            assoc_id = match.group(1)
            
    api_url = f"http://hockeycalgary.msa4.rampinteractive.com/api/leaguegame/getstandings3cached/{assoc_id}/{sid}/{game_type_id}/{cat_id}/{did}/0/0"
    
    try:
        resp = SESSION.get(api_url, timeout=HTTP_TIMEOUT)
        data = resp.json()
        return parse_ramp_json(data), api_url
    except Exception as e:
        print(f"Error fetching RAMP API: {e}")
        return [], api_url

def parse_ramp_json(data):
    standings = []
    for val in data:
        if val.get('SID') == 0: continue # Subheader
        
        try:
            entry = {
                'team': val.get('TeamName'),
                'gp': int(val.get('GamesPlayed', 0)),
                'w': int(val.get('Wins', 0)),
                'l': int(val.get('Losses', 0)),
                't': int(val.get('Ties', 0)),
                'pts': int(val.get('Points', 0)),
                'gf': int(val.get('GF', 0)),
                'ga': int(val.get('GA', 0)),
                'diff': int(val.get('GF', 0)) - int(val.get('GA', 0))
            }
            standings.append(entry)
        except (ValueError, TypeError):
            continue
    return standings

def fetch_teamlinkt_data(league_url, hierarchy_value, season_id=None, soup=None):
    # Caller can pass an already-fetched soup to avoid re-downloading the league page.
    if soup is None:
        soup = get_soup(league_url)
    if not soup: return [], None

    if not season_id:
        # Extract Season ID from the page
        sid_select = soup.find('select', id='season_id')
        if not sid_select: return [], None
        try:
            season_id = sid_select.find('option', selected=True)['value']
        except TypeError:
            options = sid_select.find_all('option')
            if options:
                season_id = options[0]['value']
            else:
                return [], None
    
    # Extract Association ID from URL or script
    script_content = ""
    for s in soup.find_all('script'):
        if s.string and 'getStandings' in s.string:
            script_content = s.string
            break
            
    assoc_id = "23957" # Default
    if script_content:
        match = re.search(r"/leagues/getStandings/(\d+)/", script_content)
        if match:
            assoc_id = match.group(1)
            
    api_url = f"https://leagues.teamlinkt.com/leagues/getStandings/{assoc_id}/{season_id}"
    
    # Prepare payload
    parts = hierarchy_value.split('-')
    payload = {
        'season_id': season_id
    }
    if len(parts) >= 1: payload['group_ids[division]'] = parts[0]
    if len(parts) >= 2: payload['group_ids[tier]'] = parts[1]
    
    headers = {
        'Referer': league_url,
        'X-Requested-With': 'XMLHttpRequest'
    }

    try:
        # print(f"DEBUG: Fetching TeamLinkt API: {api_url} with payload {payload}")
        resp = SESSION.post(api_url, data=payload, headers=headers, timeout=HTTP_TIMEOUT)
        # print(f"DEBUG: Status: {resp.status_code}")
        
        try:
            data = resp.json()
        except Exception as json_err:
            print(f"Error decoding JSON from TeamLinkt. Status: {resp.status_code}")
            print(f"Response text preview: {resp.text[:500]}")
            raise json_err
            
        # Handle case where data is a string
        if isinstance(data, str):
            # print("DEBUG: Data is string, parsing...")
            data = json.loads(data)
            
        return parse_teamlinkt_json(data), api_url
    except Exception as e:
        print(f"Error fetching TeamLinkt API: {e}")
        return [], api_url

def parse_teamlinkt_json(data):
    standings = []
    if 'standings' not in data: return []
    
    for row in data['standings']:
        try:
            team_name_raw = row.get('team_name')
            # Clean HTML from team name
            if team_name_raw and '<' in team_name_raw:
                soup = BeautifulSoup(team_name_raw, 'html.parser')
                team_name = soup.get_text(strip=True)
            else:
                team_name = team_name_raw

            entry = {
                'team': team_name,
                'gp': int(row.get('games_played', 0)),
                'w': int(row.get('total_wins', 0)),
                'l': int(row.get('total_losses', 0)),
                't': int(row.get('total_ties', 0)),
                'pts': int(row.get('total_points', 0)),
                'gf': int(row.get('score_for', 0)),
                'ga': int(row.get('score_against', 0)),
                'diff': int(row.get('score_for', 0)) - int(row.get('score_against', 0))
            }
            standings.append(entry)
        except (ValueError, TypeError):
            continue
    return standings

def save_standings(db, data, season, league, community_map, source_url=None):
    if not data:
        return

    # 1. Filter out teams whose community we can't resolve.
    rows = []
    for entry in data:
        comm_name = normalize_community_name(entry['team'], community_map)
        if comm_name:
            rows.append((entry, comm_name))

    if not rows:
        return

    print(f"  Saving {len(rows)} teams for {season.name} - {league.name}")

    # 2. Preload existing communities and teams in one query each.
    needed_comms = {comm_name for _, comm_name in rows}
    needed_teams = {entry['team'] for entry, _ in rows}

    comm_by_name = {
        c.name: c
        for c in db.query(Community).filter(Community.name.in_(needed_comms)).all()
    }
    team_by_name = {
        t.name: t
        for t in db.query(Team).filter(Team.name.in_(needed_teams)).all()
    }

    # 3. Create missing communities (race-safe — another worker may have just inserted).
    for comm_name in needed_comms - comm_by_name.keys():
        comm, _ = get_or_create(db, Community, name=comm_name)
        comm_by_name[comm_name] = comm

    # 4. Create missing teams (need community_id, so do this after communities exist).
    for entry, comm_name in rows:
        team_name = entry['team']
        if team_name in team_by_name:
            team = team_by_name[team_name]
            if team.community_id != comm_by_name[comm_name].id:
                team.community_id = comm_by_name[comm_name].id
        else:
            team, _ = get_or_create(
                db, Team,
                defaults={'community_id': comm_by_name[comm_name].id},
                name=team_name,
            )
            team_by_name[team_name] = team

    # 5. Preload existing standings for this (season, league).
    team_ids = [team_by_name[entry['team']].id for entry, _ in rows]
    existing_standings = {
        s.team_id: s
        for s in db.query(Standing).filter(
            Standing.season_id == season.id,
            Standing.league_id == league.id,
            Standing.team_id.in_(team_ids),
        ).all()
    }

    # 6. Update or insert each standing — one commit at the end.
    for entry, comm_name in rows:
        team = team_by_name[entry['team']]
        standing = existing_standings.get(team.id)
        if standing is None:
            standing = Standing(
                season_id=season.id,
                league_id=league.id,
                team_id=team.id,
            )
            db.add(standing)

        # Snapshot the community attribution as of this scrape.
        standing.community_id = comm_by_name[comm_name].id
        standing.gp = entry['gp']
        standing.w = entry['w']
        standing.l = entry['l']
        standing.t = entry['t']
        standing.pts = entry['pts']
        standing.gf = entry['gf']
        standing.ga = entry['ga']
        standing.diff = entry['diff']
        if source_url:
            standing.source_url = source_url

    try:
        db.commit()
    except IntegrityError:
        # Concurrent worker raced us on a (season, league, team_id) unique constraint.
        # Roll back and re-do this league with the now-visible existing rows.
        db.rollback()
        save_standings(db, data, season, league, community_map, source_url)

def process_league(league_info, community_map, processed_leagues, processed_lock, failed_leagues=None, failed_lock=None):
    # Create a new session for this thread
    db = SessionLocal()
    
    try:
        # Legacy discovery emits the same (slug, stream, type) once per historical year,
        # but process_league handles all seasons internally — so the duplicates are wasted
        # work. RAMP/TeamLinkt discovery should be unique by construction; if it isn't,
        # skipping is still safe (process_league iterates seasons internally there too).
        league_key = f"{league_info['slug']}-{league_info['stream']}-{league_info['type']}"

        with processed_lock:
            if league_key in processed_leagues:
                return
            processed_leagues.add(league_key)
        
        print(f"Processing {league_info['name']} ({league_info['stream']})...")
        
        # Get or create League
        league, _ = get_or_create(
            db, League,
            defaults={'name': league_info['name']},
            slug=league_info['slug'],
            stream=league_info['stream'],
            type=league_info['type'],
        )

        # Determine seasons and fetch data
        if league_info['stream'] == 'RAMP':
            # Fetch the page to find available seasons and game types
            soup = get_soup(league_info['url'])
            if not soup: return

            # 1. Find Seasons
            ramp_seasons = []
            season_select = soup.find('select', id='ddlSeason')
            if season_select:
                for opt in season_select.find_all('option'):
                    val = opt.get('value')
                    text = opt.get_text(strip=True)
                    if val and val != '0':
                        ramp_seasons.append({'name': text, 'id': val})
            
            # If no seasons found, default to current (fallback)
            if not ramp_seasons:
                print(f"  WARN: RAMP season discovery failed for {league_info['url']}, falling back to {CURRENT_SEASON}")
                ramp_seasons.append({'name': CURRENT_SEASON, 'id': None})

            # 2. Find Game Types
            game_types = []
            gt_select = soup.find('select', id='ddlGameType')
            if gt_select:
                for opt in gt_select.find_all('option'):
                    val = opt.get('value')
                    text = opt.get_text(strip=True)
                    if val and val != '0': # Skip "All Game Types"
                        game_types.append({'name': text, 'id': val})
            
            # If no game types, use default 0
            if not game_types:
                game_types.append({'name': 'Regular', 'id': 0})

            # Iterate Seasons
            for r_season in ramp_seasons:
                season_name = r_season['name']
                season_id = r_season['id']

                season, _ = get_or_create(db, Season, name=season_name)

                # Iterate Game Types
                for gt in game_types:
                    print(f"  Fetching RAMP {season_name} - {gt['name']} (SID: {season_id}, GTID: {gt['id']})...")
                    
                    # Determine League (Create specific if needed)
                    if gt['id'] == 0:
                        target_league = league
                    else:
                        specific_league_name = f"{league_info['name']} - {gt['name']}"
                        specific_league_slug = f"{league_info['slug']}-{gt['name'].lower()}"
                        specific_league_type = 'Seeding' if 'Seeding' in gt['name'] else 'Regular'

                        target_league, _ = get_or_create(
                            db, League,
                            defaults={'name': specific_league_name},
                            slug=specific_league_slug,
                            stream='RAMP',
                            type=specific_league_type,
                        )

                    data, source_url = fetch_ramp_data(league_info['url'], gt['id'], season_id, soup=soup)
                    save_standings(db, data, season, target_league, community_map, source_url)

        elif league_info['stream'] == 'TeamLinkt':
            # Fetch the page to find available seasons (e.g. Seeding vs Regular)
            soup = get_soup(league_info['url'])
            if not soup: return []
            
            tl_seasons = []
            sid_select = soup.find('select', id='season_id')
            if sid_select:
                for opt in sid_select.find_all('option'):
                    val = opt.get('value')
                    text = opt.get_text(strip=True)
                    if val:
                        tl_seasons.append({'name': text, 'id': val})
            
            # If no seasons found, try default logic (though unlikely if page loaded)
            if not tl_seasons:
                print(f"  WARN: TeamLinkt season discovery failed for {league_info['url']}, falling back to {CURRENT_SEASON}")
                tl_seasons.append({'name': CURRENT_SEASON, 'id': None})

            for tl_season in tl_seasons:
                # Parse season name and type from text like "2025/2026 U13 SEEDING"
                s_text = tl_season['name']
                season_name = CURRENT_SEASON # Default
                
                # Try to extract year
                year_match = re.search(r"(\d{4})[-/](\d{4})", s_text)
                if year_match:
                    season_name = f"{year_match.group(1)}-{year_match.group(2)}"
                
                # Determine Type
                l_type = 'Regular'
                if 'SEEDING' in s_text.upper():
                    l_type = 'Seeding'
                elif 'PLAYOFF' in s_text.upper():
                    l_type = 'Playoff'
                elif 'TOURNAMENT' in s_text.upper():
                    l_type = 'Tournament'
                
                season, _ = get_or_create(db, Season, name=season_name)

                # Determine League (specific to type; schema uses (slug, stream, type) as unique).
                target_league_name = league_info['name']
                if l_type != 'Regular':
                    target_league_name = f"{league_info['name']} - {l_type}"

                league, _ = get_or_create(
                    db, League,
                    defaults={'name': target_league_name},
                    slug=league_info['slug'],
                    stream='TeamLinkt',
                    type=l_type,
                )

                print(f"  Fetching TeamLinkt {season_name} - {l_type} (SID: {tl_season['id']})...")
                data, source_url = fetch_teamlinkt_data(league_info['url'], league_info['slug'], season_id=tl_season['id'], soup=soup)
                save_standings(db, data, season, league, community_map, source_url)
                
        else:
            # Legacy/Standard
            
            # 1. Always try the base URL plus explicit /type/seeding and /type/playoff
            #    variants. We used to rely on discovering type-links from the base page,
            #    but some pages (notably elite-council) don't render them — and
            #    community-council pages don't always link to /type/seeding even when
            #    the seeding data exists at that URL.
            base = league_info['url']
            urls_to_process = [
                base,
                f"{base}/type/seeding",
                f"{base}/type/playoff",
            ]
            base_soup = get_soup(base)

            # Collect season slugs as we go, so we don't have to re-fetch at the end
            # to return them for tournament discovery.
            collected_season_slugs = []

            # 2. Process each variation
            for url in urls_to_process:
                # Determine type from URL
                current_type = 'Regular'
                if '/type/seeding' in url:
                    current_type = 'Seeding'
                elif '/type/playoff' in url:
                    current_type = 'Playoff'
                elif '/type/tournament' in url:
                    current_type = 'Tournament'

                # Check if "Regular" URL is actually showing Seeding data
                skip_current_season_as_regular = False
                if current_type == 'Regular':
                    # Use base_soup if available and matching URL, otherwise fetch
                    if url == league_info['url'] and base_soup:
                        check_soup = base_soup
                    else:
                        check_soup = get_soup(url)

                    if check_soup:
                        active_seeding = check_soup.find('a', href=lambda h: h and '/type/seeding' in h, class_='active')
                        if active_seeding:
                            print(f"  Note: {url} defaults to 'Seeding' view. Will skip current season data for Regular.")
                            skip_current_season_as_regular = True
                
                # Get/create League for this type. The schema uses (slug, stream, type) as the
                # unique key, so the same legacy slug can produce separate Regular/Seeding/Playoff rows.
                l_name = league_info['name']
                if current_type != 'Regular' and current_type not in l_name:
                    l_name = f"{l_name} - {current_type}"

                league, _ = get_or_create(
                    db, League,
                    defaults={'name': l_name},
                    slug=league_info['slug'],
                    stream=league_info['stream'],
                    type=current_type,
                )

                seasons = get_seasons_for_league(url)

                # Fallback when the page doesn't render a server-side season selector
                # (e.g. elite-council pages): synthesize season entries from our known
                # list. Each per-season URL ends up being <base>/season/<season>, which
                # the get_soup loop below will rewrite to include /type/<type>.
                if not seasons:
                    base_for_seasons = re.sub(r'/type/[^/]+', '', url).rstrip('/')
                    seasons = [
                        {'name': y, 'slug': y, 'url': f"{base_for_seasons}/season/{y}"}
                        for y in [CURRENT_SEASON] + HISTORICAL_YEARS
                    ]

                for s in seasons:
                    if s['slug'] not in collected_season_slugs:
                        collected_season_slugs.append(s['slug'])
                for season_info in seasons:
                    # Skip CURRENT_SEASON for legacy sources IF it is U13 (sourced from TeamLinkt) or U11 (sourced from RAMP)
                    # U15 should be processed here for the current season
                    if season_info['name'] == CURRENT_SEASON:
                        # If we flagged to skip current season as regular, skip it
                        if skip_current_season_as_regular:
                            continue

                        # Check if this league is U13 or U11
                        # league_info['name'] or l_name might contain the category
                        # Or check the slug
                        is_u13 = 'u13' in league_info['slug'].lower() or 'u13' in league_info['name'].lower()
                        is_u11 = 'u11' in league_info['slug'].lower() or 'u11' in league_info['name'].lower()
                        
                        if is_u13 or is_u11:
                            continue

                    season, _ = get_or_create(db, Season, name=season_info['name'])
                    
                    # Construct target URL based on type
                    target_url = season_info['url']
                    
                    # Remove existing type if present to avoid duplication or conflict
                    target_url = re.sub(r'/type/[^/]+', '', target_url)
                    
                    if current_type == 'Regular':
                        target_url = f"{target_url}/type/league"
                    elif current_type == 'Seeding':
                        target_url = f"{target_url}/type/seeding"
                    elif current_type == 'Playoff':
                        target_url = f"{target_url}/type/playoff"
                    elif current_type == 'Tournament':
                        target_url = f"{target_url}/type/tournament"
                        
                    soup = get_soup(target_url)
                    if soup:
                        data = parse_standings(soup)
                        # Fallback to original URL if no data found and type is Regular
                        # (Some older seasons might not use /type/league)
                        if not data and current_type == 'Regular':
                             # print(f"  No data at {target_url}, trying fallback to {season_info['url']}")
                             soup_fallback = get_soup(season_info['url'])
                             if soup_fallback:
                                 data = parse_standings(soup_fallback)
                                 target_url = season_info['url'] # Update target_url if fallback used
                        
                        save_standings(db, data, season, league, community_map, target_url)
                        
            # Tournaments are linked to the main season slug — return what we collected.
            return collected_season_slugs
            
    except Exception as e:
        print(f"Error processing league {league_info['name']}: {e}")
        if failed_leagues is not None and failed_lock is not None:
            with failed_lock:
                failed_leagues.append(league_info['name'])
    finally:
        db.close()
    return []

def process_tournament(t_info, season_slug, community_map, failed_leagues=None, failed_lock=None):
    db = SessionLocal()
    try:
        print(f"  Processing {t_info['name']} ({t_info['type']})...")
        
        league, _ = get_or_create(
            db, League,
            defaults={'name': t_info['name']},
            slug=t_info['slug'],
            stream=t_info['stream'],
            type=t_info['type'],
        )

        season_name = season_slug.replace('-', '/')
        season = db.query(Season).filter_by(name=season_name).first()
        if not season:
            season = db.query(Season).filter_by(name=season_slug).first()
        # Release the read transaction before HTTP work.
        db.commit()

        if not season:
            return

        soup = get_soup(t_info['url'])
        if not soup:
            return

        data = parse_standings(soup)
        if not data:
            data = parse_brackets(soup)

        save_standings(db, data, season, league, community_map, t_info['url'])
            
    except Exception as e:
        print(f"Error processing tournament {t_info['name']}: {e}")
        if failed_leagues is not None and failed_lock is not None:
            with failed_lock:
                failed_leagues.append(f"[T] {t_info['name']}")
    finally:
        db.close()


def _ramp_division_name(link):
    """Walk up the DOM from a /division/.../standings link looking for a header."""
    curr = link.parent
    for _ in range(5):
        if not curr:
            return None
        prev = curr.find_previous_sibling(['h1', 'h2', 'h3', 'h4', 'h5', 'div'])
        if prev:
            text = prev.get_text(strip=True)
            if text and len(text) < 50 and 'Games' not in text:
                return text
        header = curr.find(['h1', 'h2', 'h3', 'h4', 'h5'])
        if header:
            text = header.get_text(strip=True)
            if text:
                return text
        curr = curr.parent
    return None


def _process_ramp_seeding_division(division, season_name, game_type_id, season_id, community_map):
    """Worker: process one RAMP division for a fixed (season, game_type)."""
    db = SessionLocal()
    try:
        season, _ = get_or_create(db, Season, name=season_name)
        league, _ = get_or_create(
            db, League,
            defaults={'name': division['league_name']},
            slug=division['league_slug'],
            stream='RAMP',
            type='Seeding',
        )
        data, source_url = fetch_ramp_data(division['full_url'], game_type_id, season_id)
        save_standings(db, data, season, league, community_map, source_url)
    except Exception as e:
        print(f"Error processing {division['league_name']}: {e}")
    finally:
        db.close()


def fetch_u11_seeding_2024_2025(community_map):
    print("Fetching U11 Seeding data for 2024-2025 (RAMP)...")
    url = "http://hockeycalgary.msa4.rampinteractive.com/division/3300/"
    soup = get_soup(url)
    if not soup:
        print("  Could not fetch U11 division list.")
        return

    season_id = "10604"        # 2024-2025
    game_type_id = "8361"      # Seeding
    season_name = "2024-2025"

    # 1. Discover all divisions (sequential, one page).
    divisions = []
    seen_slugs = set()
    for link in soup.find_all('a', href=True):
        href = link['href']
        if '/division/3300/' not in href or 'standings' not in href:
            continue
        slug = href.replace('/division/', '').replace('/standings', '')
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        found_name = _ramp_division_name(link)
        if not found_name:
            continue

        league_name = found_name if 'Seeding' in found_name else f"{found_name} - Seeding"
        divisions.append({
            'league_name': league_name,
            'league_slug': f"{slug}-seeding",
            'full_url': f"http://hockeycalgary.msa4.rampinteractive.com{href}",
        })

    print(f"  Found {len(divisions)} U11 Seeding divisions; processing in parallel...")

    # 2. Process each division in parallel.
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [
            executor.submit(_process_ramp_seeding_division, d, season_name, game_type_id, season_id, community_map)
            for d in divisions
        ]
        concurrent.futures.wait(futures)

def sync_data(reset=False, progress_callback=None):
    if progress_callback:
        progress_callback(0, "Starting sync...")

    if reset:
        print("Resetting database... Deleting all existing data.")
        if progress_callback:
            progress_callback(0, "Resetting database...")
        try:
            Base.metadata.drop_all(bind=engine)
            # Also clear Alembic's version tracking so init_db() will re-run migrations
            # to recreate the schema. (drop_all leaves alembic_version untouched.)
            with engine.begin() as conn:
                from sqlalchemy import text
                conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
            print("Database reset complete.")
        except Exception as e:
            print(f"Error resetting database: {e}")

    init_db()

    # Record this scrape run
    run_db = SessionLocal()
    scrape_run = ScrapeRun(started_at=datetime.utcnow(), status='running')
    run_db.add(scrape_run)
    run_db.commit()
    run_db.refresh(scrape_run)
    run_id = scrape_run.id
    run_db.close()

    try:
        failed = _do_sync(progress_callback)
        _finalize_scrape_run(run_id, status='success', failed_leagues=failed)
    except Exception as e:
        _finalize_scrape_run(run_id, status='failed', error_message=str(e))
        raise


def _finalize_scrape_run(run_id, status, error_message=None, failed_leagues=None):
    db = SessionLocal()
    try:
        run = db.query(ScrapeRun).filter_by(id=run_id).first()
        if not run:
            return
        run.finished_at = datetime.utcnow()
        run.status = status
        run.error_message = error_message
        run.leagues_processed = db.query(func.count(League.id)).scalar()
        run.standings_count = db.query(func.count(Standing.id)).scalar()
        if failed_leagues:
            run.leagues_failed = len(failed_leagues)
            # Truncate to keep the column reasonable
            joined = ", ".join(failed_leagues)
            run.failed_leagues = joined[:1000]
        else:
            run.leagues_failed = 0
        db.commit()
    finally:
        db.close()


def _do_sync(progress_callback=None):
    
    community_map = load_community_map()
    
    # 1. Fetch Legacy/Historical Leagues (from hockeycalgary.ca) — parallel.
    print("Fetching legacy/historical leagues...")
    if progress_callback:
        progress_callback(5, "Fetching legacy/historical leagues...")

    legacy_years = [None] + HISTORICAL_YEARS
    legacy_leagues = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        for batch in ex.map(get_leagues, legacy_years):
            legacy_leagues.extend(batch)

    print(f"Found {len(legacy_leagues)} legacy leagues (total).")
    
    # 2. Fetch RAMP Leagues (U11)
    print("Fetching RAMP leagues (U11)...")
    if progress_callback:
        progress_callback(10, "Fetching RAMP leagues...")
    ramp_leagues = get_ramp_leagues()
    print(f"Found {len(ramp_leagues)} RAMP leagues.")
    
    # 3. Fetch TeamLinkt Leagues (U13+)
    print("Fetching TeamLinkt leagues (U13+)...")
    if progress_callback:
        progress_callback(15, "Fetching TeamLinkt leagues...")
    teamlinkt_leagues = get_teamlinkt_leagues()
    print(f"Found {len(teamlinkt_leagues)} TeamLinkt leagues.")
    
    all_leagues = legacy_leagues + ramp_leagues + teamlinkt_leagues
    total_leagues = len(all_leagues)
    
    # CLEANUP: Remove legacy data for CURRENT_SEASON to avoid duplicates with TeamLinkt
    # Only remove U13 data, as U15 is still on legacy
    print(f"Cleaning up legacy data for {CURRENT_SEASON} (U13 only)...")
    db = SessionLocal()
    try:
        current = db.query(Season).filter_by(name=CURRENT_SEASON).first()
        if current:
            standings_to_delete = db.query(Standing).join(League).filter(
                Standing.season_id == current.id,
                League.stream == 'community-council',
                League.name.like('%U13%')
            ).all()

            if standings_to_delete:
                print(f"  Deleting {len(standings_to_delete)} legacy records for {CURRENT_SEASON} (U13)...")
                for st in standings_to_delete:
                    db.delete(st)
                db.commit()
            else:
                print(f"  No legacy records found for {CURRENT_SEASON} (U13).")
    except Exception as e:
        print(f"Error during cleanup: {e}")
    finally:
        db.close()
    
    processed_leagues = set() # Track processed leagues to avoid duplicates
    processed_lock = threading.Lock()
    known_seasons = set()
    failed_leagues = []           # workers append the league name on exception
    failed_lock = threading.Lock()

    if progress_callback:
        progress_callback(20, f"Processing {total_leagues} leagues...")

    completed_leagues = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for league_info in all_leagues:
            futures.append(
                executor.submit(process_league, league_info, community_map, processed_leagues, processed_lock, failed_leagues, failed_lock)
            )
            
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                known_seasons.update(result)
            
            completed_leagues += 1
            if progress_callback:
                # Map 20% -> 90%
                pct = 20 + int((completed_leagues / total_leagues) * 70)
                progress_callback(pct, f"Processed {completed_leagues}/{total_leagues} leagues...")

    # Process tournaments (Legacy only for now)
    print("Fetching tournaments...")
    if progress_callback:
        progress_callback(90, "Fetching tournaments...")

    # Discover tournaments per season in parallel (each call is one HTTP page).
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        discovery = list(executor.map(get_tournaments, known_seasons))
    tournaments_by_season = list(zip(known_seasons, discovery))
    for season_slug, t_list in tournaments_by_season:
        print(f"  {season_slug}: {len(t_list)} tournament(s)")

    # Process tournaments in parallel.
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(process_tournament, t_info, season_slug, community_map, failed_leagues, failed_lock)
            for season_slug, t_list in tournaments_by_season
            for t_info in t_list
        ]
        concurrent.futures.wait(futures)
    
    # Fetch specific U11 Seeding data for 2024-2025
    if progress_callback:
        progress_callback(95, "Fetching U11 Seeding data...")
    fetch_u11_seeding_2024_2025(community_map)

    print("Sync complete.")
    if progress_callback:
        progress_callback(100, "Sync complete.")

    return failed_leagues


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scrape Hockey Calgary / RAMP / TeamLinkt.")
    parser.add_argument(
        "--reset", action="store_true",
        help="Drop existing data before scraping (full rebuild).",
    )
    args = parser.parse_args()
    sync_data(reset=args.reset)