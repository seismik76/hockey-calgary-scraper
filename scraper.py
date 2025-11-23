import requests
from bs4 import BeautifulSoup
import time
from sqlalchemy.orm import Session
from database import init_db, SessionLocal, engine
from models import Season, League, Team, Community, Standing, Base
from utilities.utils import normalize_community_name, load_community_map, save_community_map
import urllib3
from collections import defaultdict
import re
import json

import concurrent.futures
import threading

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://www.hockeycalgary.ca"
db_lock = threading.Lock()

def get_soup(url):
    try:
        response = requests.get(url, verify=False)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def get_leagues(year=None):
    if year:
        url = f"{BASE_URL}/standings/index/season/{year}"
    else:
        url = f"{BASE_URL}/standings"
        
    soup = get_soup(url)
    if not soup:
        return []
    
    leagues = []
    # Find all links that look like league links
    # Based on inspection: /standings/index/stream/{stream}/league/{slug}
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
                
                # Filter for U9, U11, U13, U15
                if any(cat in name for cat in ['U9', 'U11', 'U13', 'U15']):
                    leagues.append({
                        'name': name,
                        'slug': slug,
                        'stream': stream,
                        'url': f"{BASE_URL}{href}",
                        'type': league_type
                    })
            except (ValueError, IndexError):
                continue
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
    """
    url = "https://leagues.teamlinkt.com/hockeycalgary/Standings"
    soup = get_soup(url)
    if not soup:
        return []
        
    leagues = []
    # Find the hierarchy_filter select
    select = soup.find('select', {'name': 'hierarchy_filter'}) or soup.find('select', {'id': 'hierarchy_filter'})
    
    if select:
        options = select.find_all('option')
        for opt in options:
            name = opt.get_text(strip=True)
            value = opt.get('value')
            if value and value != '0':
                # Exclude U15 from TeamLinkt as it is sourced from Community Council
                if 'U15' in name:
                    continue
                    
                leagues.append({
                    'name': name,
                    'slug': value,
                    'stream': 'TeamLinkt',
                    'url': f"{url}?hierarchy_filter={value}",
                    'type': 'Regular'
                })
    return leagues

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
                    
                    if any(cat in name for cat in ['U9', 'U11', 'U13', 'U15']):
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

def fetch_ramp_data(league_url, game_type_id=0, season_id=None):
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
        resp = requests.get(api_url)
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

def fetch_teamlinkt_data(league_url, hierarchy_value, season_id=None):
    # league_url is the main standings page
    if not season_id:
        soup = get_soup(league_url) # Use verify=False
        if not soup: return [], None
        
        # Extract Season ID
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
    else:
        # We still need soup to get assoc_id
        soup = get_soup(league_url)
        if not soup: return [], None
    
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
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': league_url,
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    try:
        # print(f"DEBUG: Fetching TeamLinkt API: {api_url} with payload {payload}")
        resp = requests.post(api_url, data=payload, headers=headers, verify=False)
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
        
    print(f"  Saving {len(data)} teams for {season.name} - {league.name}")
    
    for entry in data:
        team_name = entry['team']
        comm_name = normalize_community_name(team_name, community_map)
        
        if not comm_name:
            # Skip teams that don't belong to allowed communities
            continue

        community = db.query(Community).filter_by(name=comm_name).first()
        if not community:
            community = Community(name=comm_name)
            db.add(community)
            db.commit()
            db.refresh(community)
        
        team = db.query(Team).filter_by(name=team_name).first()
        if not team:
            team = Team(name=team_name, community_id=community.id)
            db.add(team)
            db.commit()
            db.refresh(team)
        elif team.community_id != community.id:
            team.community_id = community.id
            db.commit()
            
        standing = db.query(Standing).filter_by(
            season_id=season.id,
            league_id=league.id,
            team_id=team.id
        ).first()
        
        if not standing:
            standing = Standing(
                season_id=season.id,
                league_id=league.id,
                team_id=team.id
            )
            db.add(standing)
        
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
        
        db.commit()

def process_league(league_info, community_map, processed_leagues, processed_lock):
    # Create a new session for this thread
    db = SessionLocal()
    
    try:
        league_key = f"{league_info['slug']}-{league_info['stream']}-{league_info['type']}"
        
        with processed_lock:
            if league_key in processed_leagues and league_info['stream'] not in ['RAMP', 'TeamLinkt']:
                return
            processed_leagues.add(league_key)
        
        print(f"Processing {league_info['name']} ({league_info['stream']})...")
        
        # Get or create League
        with db_lock:
            league = db.query(League).filter_by(
                slug=league_info['slug'], 
                stream=league_info['stream'],
                type=league_info['type']
            ).first()
            
            if not league:
                league = League(
                    name=league_info['name'], 
                    slug=league_info['slug'], 
                    stream=league_info['stream'],
                    type=league_info['type']
                )
                db.add(league)
                db.commit()
                db.refresh(league)
            
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
            
            # If no seasons found, default to current (hardcoded fallback)
            if not ramp_seasons:
                ramp_seasons.append({'name': "2025-2026", 'id': None})

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
                
                # Ensure season exists in DB
                with db_lock:
                    season = db.query(Season).filter_by(name=season_name).first()
                    if not season:
                        season = Season(name=season_name)
                        db.add(season)
                        db.commit()
                        db.refresh(season)
                
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
                        
                        with db_lock:
                            target_league = db.query(League).filter_by(
                                slug=specific_league_slug,
                                stream='RAMP',
                                type=specific_league_type
                            ).first()
                            
                            if not target_league:
                                target_league = League(
                                    name=specific_league_name,
                                    slug=specific_league_slug,
                                    stream='RAMP',
                                    type=specific_league_type
                                )
                                db.add(target_league)
                                db.commit()
                                db.refresh(target_league)
                    
                    data, source_url = fetch_ramp_data(league_info['url'], gt['id'], season_id)
                    with db_lock:
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
                # Fallback to just one pass with default
                tl_seasons.append({'name': "2025-2026", 'id': None})

            for tl_season in tl_seasons:
                # Parse season name and type from text like "2025/2026 U13 SEEDING"
                # We want to map this to our standard Season "2025-2026" and League Type
                
                s_text = tl_season['name']
                season_name = "2025-2026" # Default
                
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
                
                # Ensure Season exists
                with db_lock:
                    season = db.query(Season).filter_by(name=season_name).first()
                    if not season:
                        season = Season(name=season_name)
                        db.add(season)
                        db.commit()
                        db.refresh(season)
                
                # Determine League (Specific to Type)
                # If type is Regular, use the base league.
                # If type is Seeding, we might need a separate league entry or just use the type column?
                # The current schema uses (slug, stream, type) as unique.
                # So we should create/get the league with the correct type.
                
                # Construct a name that might include the type if not Regular, 
                # similar to how we did for Legacy/RAMP to distinguish in UI if needed.
                # But for TeamLinkt, the league_info['name'] is like "U13 / U13 TIER 3 SOUTH"
                # If we have Seeding, we probably want "U13 / U13 TIER 3 SOUTH - Seeding"
                
                target_league_name = league_info['name']
                if l_type != 'Regular':
                    target_league_name = f"{league_info['name']} - {l_type}"
                
                with db_lock:
                    league = db.query(League).filter_by(
                        slug=league_info['slug'], 
                        stream='TeamLinkt',
                        type=l_type
                    ).first()
                    
                    if not league:
                        league = League(
                            name=target_league_name,
                            slug=league_info['slug'],
                            stream='TeamLinkt',
                            type=l_type
                        )
                        db.add(league)
                        db.commit()
                        db.refresh(league)
                
                print(f"  Fetching TeamLinkt {season_name} - {l_type} (SID: {tl_season['id']})...")
                data, source_url = fetch_teamlinkt_data(league_info['url'], league_info['slug'], season_id=tl_season['id'])
                with db_lock:
                    save_standings(db, data, season, league, community_map, source_url)
                
        else:
            # Legacy/Standard
            
            # 1. Discover all variations (Regular, Seeding, Playoff)
            urls_to_process = {league_info['url']}
            base_soup = get_soup(league_info['url'])
            if base_soup:
                for a in base_soup.find_all('a', href=True):
                    href = a['href']
                    # Look for sibling links (same league, different type)
                    if '/league/' in href and league_info['slug'] in href:
                        if '/type/' in href:
                             urls_to_process.add(f"{BASE_URL}{href}")

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
                        # Check if there is an ACTIVE link to seeding
                        # This implies the page is defaulting to Seeding view
                        active_seeding = check_soup.find('a', href=lambda h: h and '/type/seeding' in h, class_='active')
                        if active_seeding:
                            print(f"  Note: {url} defaults to 'Seeding' view. Will skip current season data for Regular.")
                            skip_current_season_as_regular = True
                
                # Create/Get League for this specific type
                # Note: The original league_info might be for Regular, but here we might be processing Seeding
                
                # We need a unique slug for the DB if we want to separate them?
                # The League model has (slug, stream, type) as unique constraint effectively?
                # Let's check models.py or the DB schema.
                # The code uses:
                # league = db.query(League).filter_by(slug=..., stream=..., type=...).first()
                # So yes, we can have same slug, same stream, different type.
                
                with db_lock:
                    league = db.query(League).filter_by(
                        slug=league_info['slug'], 
                        stream=league_info['stream'],
                        type=current_type
                    ).first()
                    
                    if not league:
                        # Append type to name if not Regular to make it clear?
                        # Or just keep name same and rely on type column?
                        # The UI groups by League Name. If they have same name but different type, 
                        # they will be grouped together in dropdowns unless we filter by type.
                        # Let's keep name consistent or append type?
                        # Existing code for RAMP appended type: f"{league_info['name']} - {gt['name']}"
                        # Let's append type for clarity if not Regular.
                        
                        l_name = league_info['name']
                        # If the name already has "Seeding" in it, don't add it again.
                        if current_type != 'Regular' and current_type not in l_name:
                             l_name = f"{l_name} - {current_type}"
                             
                        league = League(
                            name=l_name, 
                            slug=league_info['slug'], 
                            stream=league_info['stream'],
                            type=current_type
                        )
                        db.add(league)
                        db.commit()
                        db.refresh(league)

                seasons = get_seasons_for_league(url)
                for season_info in seasons:
                    # Skip 2025-2026 for legacy sources IF it is U13 (sourced from TeamLinkt) or U11 (sourced from RAMP)
                    # U15 should be processed here for 2025-2026
                    if season_info['name'] == '2025-2026':
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

                    # Note: known_seasons tracking is tricky in parallel. 
                    # We might need to return known seasons from this function or use a shared set.
                    # For now, let's just process.
                    
                    with db_lock:
                        season = db.query(Season).filter_by(name=season_info['name']).first()
                        if not season:
                            season = Season(name=season_info['name'])
                            db.add(season)
                            db.commit()
                            db.refresh(season)
                    
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
                        
                        with db_lock:
                            save_standings(db, data, season, league, community_map, target_url)
                        
            # Return known seasons for tournament processing (from the main url)
            # This is a bit loose but tournaments are usually linked to the main season slug
            return [s['slug'] for s in get_seasons_for_league(league_info['url'])]
            
    except Exception as e:
        print(f"Error processing league {league_info['name']}: {e}")
    finally:
        db.close()
    return []

def process_tournament(t_info, season_slug, community_map):
    db = SessionLocal()
    try:
        print(f"  Processing {t_info['name']} ({t_info['type']})...")
        
        with db_lock:
            league = db.query(League).filter_by(
                slug=t_info['slug'], 
                stream=t_info['stream'],
                type=t_info['type']
            ).first()
            
            if not league:
                league = League(
                    name=t_info['name'], 
                    slug=t_info['slug'], 
                    stream=t_info['stream'],
                    type=t_info['type']
                )
                db.add(league)
                db.commit()
                db.refresh(league)
        
        season_name = season_slug.replace('-', '/')
        with db_lock:
            season = db.query(Season).filter_by(name=season_name).first()
            if not season:
                season = db.query(Season).filter_by(name=season_slug).first()
        
        if not season:
            return

        soup = get_soup(t_info['url'])
        if not soup:
            return
        
        data = parse_standings(soup)
        if not data:
            # print(f"    No standings table found, trying brackets parser...")
            data = parse_brackets(soup)
            
        with db_lock:
            save_standings(db, data, season, league, community_map, t_info['url'])
            
    except Exception as e:
        print(f"Error processing tournament {t_info['name']}: {e}")
    finally:
        db.close()

def fetch_u11_seeding_2024_2025(community_map):
    print("Fetching U11 Seeding data for 2024-2025 (RAMP)...")
    url = "http://hockeycalgary.msa4.rampinteractive.com/division/3300/"
    soup = get_soup(url)
    if not soup:
        print("  Could not fetch U11 division list.")
        return

    # Find all division links
    # They look like /division/3300/XXXXX/standings
    links = soup.find_all('a', href=True)
    
    season_id = "10604" # 2024-2025
    game_type_id = "8361" # Seeding
    season_name = "2024-2025"
    
    db = SessionLocal()
    try:
        # Ensure Season exists
        with db_lock:
            season = db.query(Season).filter_by(name=season_name).first()
            if not season:
                season = Season(name=season_name)
                db.add(season)
                db.commit()
                db.refresh(season)
        
        processed_slugs = set()

        for link in links:
            href = link['href']
            if '/division/3300/' in href and 'standings' in href:
                # Extract Division Name
                # The link text is usually "Standings", we need to find the header
                # Similar logic to get_ramp_leagues
                
                # Traverse up to find a header for the league name
                parent = link.parent
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
                
                if not found_name:
                    continue
                    
                full_url = f"http://hockeycalgary.msa4.rampinteractive.com{href}"
                slug = href.replace('/division/', '').replace('/standings', '')
                
                if slug in processed_slugs:
                    continue
                processed_slugs.add(slug)

                # Construct League Name and Slug
                # Ensure we don't duplicate "Seeding" in the name if it's already there
                if "Seeding" in found_name:
                    league_name = found_name
                else:
                    league_name = f"{found_name} - Seeding"
                    
                league_slug = f"{slug}-seeding"
                league_stream = "RAMP"
                league_type = "Seeding"
                
                print(f"  Processing {league_name}...")
                
                with db_lock:
                    league = db.query(League).filter_by(
                        slug=league_slug,
                        stream=league_stream,
                        type=league_type
                    ).first()
                    
                    if not league:
                        league = League(
                            name=league_name,
                            slug=league_slug,
                            stream=league_stream,
                            type=league_type
                        )
                        db.add(league)
                        db.commit()
                        db.refresh(league)
                
                # Fetch Data
                data, source_url = fetch_ramp_data(full_url, game_type_id, season_id)
                with db_lock:
                    save_standings(db, data, season, league, community_map, source_url)
                    
    except Exception as e:
        print(f"Error fetching U11 Seeding 2024-2025: {e}")
    finally:
        db.close()

def sync_data(reset=False):
    if reset:
        print("Resetting database... Deleting all existing data.")
        try:
            Base.metadata.drop_all(bind=engine)
            print("Database reset complete.")
        except Exception as e:
            print(f"Error resetting database: {e}")

    init_db()
    
    community_map = load_community_map()
    
    # 1. Fetch Legacy/Historical Leagues (from hockeycalgary.ca)
    print("Fetching legacy/historical leagues...")
    legacy_leagues = get_leagues() # Current season
    
    # Add historical seasons
    historical_years = ["2023-2024", "2022-2023", "2021-2022", "2020-2021"]
    for year in historical_years:
        print(f"Fetching legacy leagues for {year}...")
        legacy_leagues.extend(get_leagues(year))
        
    print(f"Found {len(legacy_leagues)} legacy leagues (total).")
    
    # 2. Fetch RAMP Leagues (U11)
    print("Fetching RAMP leagues (U11)...")
    ramp_leagues = get_ramp_leagues()
    print(f"Found {len(ramp_leagues)} RAMP leagues.")
    
    # 3. Fetch TeamLinkt Leagues (U13+)
    print("Fetching TeamLinkt leagues (U13+)...")
    teamlinkt_leagues = get_teamlinkt_leagues()
    print(f"Found {len(teamlinkt_leagues)} TeamLinkt leagues.")
    
    all_leagues = legacy_leagues + ramp_leagues + teamlinkt_leagues
    
    # CLEANUP: Remove legacy data for 2025-2026 to avoid duplicates with TeamLinkt
    # Only remove U13 data, as U15 is still on legacy
    print("Cleaning up legacy data for 2025-2026 (U13 only)...")
    db = SessionLocal()
    try:
        # Find 2025-2026 season
        s25 = db.query(Season).filter_by(name="2025-2026").first()
        if s25:
            # Find standings for this season where league stream is community-council AND league name contains U13
            # We need to join with League
            standings_to_delete = db.query(Standing).join(League).filter(
                Standing.season_id == s25.id,
                League.stream == 'community-council',
                League.name.like('%U13%')
            ).all()
            
            if standings_to_delete:
                print(f"  Deleting {len(standings_to_delete)} legacy records for 2025-2026 (U13)...")
                for st in standings_to_delete:
                    db.delete(st)
                db.commit()
            else:
                print("  No legacy records found for 2025-2026 (U13).")
    except Exception as e:
        print(f"Error during cleanup: {e}")
    finally:
        db.close()
    
    processed_leagues = set() # Track processed leagues to avoid duplicates
    processed_lock = threading.Lock()
    known_seasons = set()
    
    # Use ThreadPoolExecutor for parallel processing
    # Adjust max_workers based on your system capabilities and network limits
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for league_info in all_leagues:
            futures.append(
                executor.submit(process_league, league_info, community_map, processed_leagues, processed_lock)
            )
            
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                known_seasons.update(result)

    # Process tournaments (Legacy only for now)
    print("Fetching tournaments...")
    
    # Parallelize tournaments too
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for season_slug in known_seasons:
            print(f"Checking tournaments for {season_slug}...")
            tournaments = get_tournaments(season_slug)
            for t_info in tournaments:
                futures.append(
                    executor.submit(process_tournament, t_info, season_slug, community_map)
                )
        
        concurrent.futures.wait(futures)
    
    # Fetch specific U11 Seeding data for 2024-2025
    fetch_u11_seeding_2024_2025(community_map)

    print("Sync complete.")

if __name__ == "__main__":
    sync_data()