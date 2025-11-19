import requests
from bs4 import BeautifulSoup
import time
from sqlalchemy.orm import Session
from database import init_db, SessionLocal
from models import Season, League, Team, Community, Standing
from utils import normalize_community_name, load_community_map, save_community_map
import urllib3
from collections import defaultdict
import re
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://www.hockeycalgary.ca"

def get_soup(url):
    try:
        response = requests.get(url, verify=False)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def get_leagues():
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

def fetch_ramp_data(league_url):
    soup = get_soup(league_url)
    if not soup: return []
    
    # Extract SID
    sid_select = soup.find('select', id='ddlSeason')
    if not sid_select: return []
    try:
        sid = sid_select.find('option', selected=True)['value']
    except TypeError:
        # Fallback if no option is explicitly selected (use first)
        options = sid_select.find_all('option')
        if options:
            sid = options[0]['value']
        else:
            return []
    
    # Extract DID from URL
    # URL: .../division/3300/30078/standings
    parts = league_url.split('/')
    try:
        if 'division' in parts:
            did_idx = parts.index('division') + 2
            did = parts[did_idx]
            cat_id = parts[did_idx-1] # 3300
        else:
            return []
    except:
        return []
        
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
            
    api_url = f"http://hockeycalgary.msa4.rampinteractive.com/api/leaguegame/getstandings3cached/{assoc_id}/{sid}/0/{cat_id}/{did}/0/0"
    
    try:
        resp = requests.get(api_url)
        data = resp.json()
        return parse_ramp_json(data)
    except Exception as e:
        print(f"Error fetching RAMP API: {e}")
        return []

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

def fetch_teamlinkt_data(league_url, hierarchy_value):
    # league_url is the main standings page
    soup = get_soup(league_url) # Use verify=False
    if not soup: return []
    
    # Extract Season ID
    sid_select = soup.find('select', id='season_id')
    if not sid_select: return []
    try:
        season_id = sid_select.find('option', selected=True)['value']
    except TypeError:
        options = sid_select.find_all('option')
        if options:
            season_id = options[0]['value']
        else:
            return []
    
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
            
        return parse_teamlinkt_json(data)
    except Exception as e:
        print(f"Error fetching TeamLinkt API: {e}")
        return []

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

def save_standings(db, data, season, league, community_map):
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
        
        db.commit()

def sync_data():
    init_db()
    db = SessionLocal()
    
    community_map = load_community_map()
    
    # 1. Fetch Legacy/Historical Leagues (from hockeycalgary.ca)
    print("Fetching legacy/historical leagues...")
    legacy_leagues = get_leagues()
    print(f"Found {len(legacy_leagues)} legacy leagues.")
    
    # 2. Fetch RAMP Leagues (U11)
    print("Fetching RAMP leagues (U11)...")
    ramp_leagues = get_ramp_leagues()
    print(f"Found {len(ramp_leagues)} RAMP leagues.")
    
    # 3. Fetch TeamLinkt Leagues (U13+)
    print("Fetching TeamLinkt leagues (U13+)...")
    teamlinkt_leagues = get_teamlinkt_leagues()
    print(f"Found {len(teamlinkt_leagues)} TeamLinkt leagues.")
    
    all_leagues = legacy_leagues + ramp_leagues + teamlinkt_leagues
    
    known_seasons = set()
    
    for league_info in all_leagues:
        print(f"Processing {league_info['name']} ({league_info['stream']})...")
        
        # Get or create League
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
            current_season_name = "2025-2026" 
            season = db.query(Season).filter_by(name=current_season_name).first()
            if not season:
                season = Season(name=current_season_name)
                db.add(season)
                db.commit()
                db.refresh(season)
                
            data = fetch_ramp_data(league_info['url'])
            save_standings(db, data, season, league, community_map)
                
        elif league_info['stream'] == 'TeamLinkt':
            current_season_name = "2025-2026"
            season = db.query(Season).filter_by(name=current_season_name).first()
            if not season:
                season = Season(name=current_season_name)
                db.add(season)
                db.commit()
                db.refresh(season)
                
            data = fetch_teamlinkt_data(league_info['url'], league_info['slug'])
            save_standings(db, data, season, league, community_map)
                
        else:
            # Legacy/Standard
            seasons = get_seasons_for_league(league_info['url'])
            for season_info in seasons:
                known_seasons.add(season_info['slug'])
                
                season = db.query(Season).filter_by(name=season_info['name']).first()
                if not season:
                    season = Season(name=season_info['name'])
                    db.add(season)
                    db.commit()
                    db.refresh(season)
                    
                soup = get_soup(season_info['url'])
                if soup:
                    data = parse_standings(soup)
                    save_standings(db, data, season, league, community_map)

    # Process tournaments (Legacy only for now)
    print("Fetching tournaments...")
    for season_slug in known_seasons:
        print(f"Checking tournaments for {season_slug}...")
        tournaments = get_tournaments(season_slug)
        for t_info in tournaments:
            print(f"  Processing {t_info['name']} ({t_info['type']})...")
            
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
            season = db.query(Season).filter_by(name=season_name).first()
            if not season:
                season = db.query(Season).filter_by(name=season_slug).first()
                if not season:
                    continue

            soup = get_soup(t_info['url'])
            if not soup:
                continue
            
            data = parse_standings(soup)
            save_standings(db, data, season, league, community_map)
    
    db.close()
    print("Sync complete.")

if __name__ == "__main__":
    sync_data()