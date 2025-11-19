import requests
from bs4 import BeautifulSoup
import time
from sqlalchemy.orm import Session
from database import init_db, SessionLocal
from models import Season, League, Team, Community, Standing
from utils import normalize_community_name, load_community_map, save_community_map
import urllib3

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
            # href might be /standings/index/stream/community-council/league/u11-tier-1
            # parts: ['', 'standings', 'index', 'stream', 'community-council', 'league', 'u11-tier-1']
            try:
                stream_idx = parts.index('stream') + 1
                league_idx = parts.index('league') + 1
                stream = parts[stream_idx]
                slug = parts[league_idx]
                name = a.get_text(strip=True)
                
                # Filter for U9, U11, U13, U15
                if any(cat in name for cat in ['U9', 'U11', 'U13', 'U15']):
                    leagues.append({
                        'name': name,
                        'slug': slug,
                        'stream': stream,
                        'url': f"{BASE_URL}{href}"
                    })
            except (ValueError, IndexError):
                continue
    return leagues

def get_seasons_for_league(league_url):
    soup = get_soup(league_url)
    if not soup:
        return []
    
    seasons = []
    # Look for the season selector
    # It was a select option with value like /standings/index/stream/.../season/2021-2022
    options = soup.find_all('option')
    for option in options:
        value = option.get('value')
        text = option.get_text(strip=True)
        if value and '/season/' in value:
            # Extract season name from text or value
            # value: .../season/2021-2022
            season_slug = value.split('/season/')[-1]
            seasons.append({
                'name': text, # e.g. "2021/2022"
                'slug': season_slug, # e.g. "2021-2022"
                'url': f"{BASE_URL}{value}"
            })
            
    # If no selector found, maybe it's just the current season?
    # But usually there is a selector if history exists.
    # If not, we can assume current season.
    # But let's return what we found.
    return seasons

def parse_standings(soup):
    standings_data = []
    # Find the standings table
    # Usually has class "standings" or similar, or just look for headers
    table = soup.find('table', class_='table') # Generic guess, might need refinement
    
    # If multiple tables, we need to find the right one.
    # Look for headers: GP, W, L, PTS or Games played, Wins, etc.
    tables = soup.find_all('table')
    target_table = None
    for t in tables:
        headers = [th.get_text(strip=True) for th in t.find_all('th')]
        # Check for key headers
        if ('GP' in headers or 'Games played' in headers) and ('PTS' in headers or 'points' in headers):
            target_table = t
            break
            
    if not target_table:
        return []
        
    # Parse rows
    rows = target_table.find_all('tr')
    headers = [th.get_text(strip=True) for th in rows[0].find_all('th')]
    
    # Map headers to keys
    header_map = {
        'Team': 'team',
        'GP': 'gp',
        'Games played': 'gp',
        'W': 'w',
        'Wins': 'w',
        'L': 'l',
        'losses': 'l',
        'Losses': 'l',
        'T': 't',
        'ties': 't',
        'Ties': 't',
        'PTS': 'pts',
        'points': 'pts',
        'Points': 'pts',
        'GF': 'gf',
        'goals for': 'gf',
        'Goals For': 'gf',
        'GA': 'ga',
        'goals against': 'ga',
        'Goals Against': 'ga',
        'Diff': 'diff',
        'DIFF': 'diff',
        'Goal Differential': 'diff'
    }
    
    col_indices = {}
    for idx, h in enumerate(headers):
        # Normalize header text
        h_clean = h.strip()
        if h_clean in header_map:
            col_indices[header_map[h_clean]] = idx
        # Also try lowercase
        elif h_clean.lower() in header_map:
             col_indices[header_map[h_clean.lower()]] = idx
            
    if 'team' not in col_indices:
        return []
        
    for row in rows[1:]:
        cols = row.find_all('td')
        if not cols:
            continue
            
        # Check if row says "There are no standings available"
        if len(cols) == 1 and "no standings available" in cols[0].get_text():
            continue

        # Sometimes rows are headers for divisions, skip them
        # But be careful, sometimes they are just short rows
        if len(cols) < 3: # Arbitrary small number
            continue
            
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
            
            # Calculate diff if not present
            if 'diff' in col_indices:
                entry['diff'] = int(cols[col_indices['diff']].get_text(strip=True) or 0)
            else:
                entry['diff'] = entry['gf'] - entry['ga']
            
            standings_data.append(entry)
        except (ValueError, IndexError) as e:
            # print(f"Skipping row: {e}")
            continue
            
    return standings_data

def sync_data():
    init_db()
    db = SessionLocal()
    
    print("Fetching leagues...")
    leagues = get_leagues()
    print(f"Found {len(leagues)} leagues.")
    
    community_map = load_community_map()
    
    for league_info in leagues:
        print(f"Processing {league_info['name']}...")
        
        # Get or create League
        league = db.query(League).filter_by(slug=league_info['slug'], stream=league_info['stream']).first()
        if not league:
            league = League(name=league_info['name'], slug=league_info['slug'], stream=league_info['stream'])
            db.add(league)
            db.commit()
            db.refresh(league)
            
        # Get seasons
        seasons = get_seasons_for_league(league_info['url'])
        if not seasons:
            # If no seasons found, maybe just current page is the only one?
            # Or maybe we failed to parse.
            # Let's assume the current URL is the current season.
            # But we need a season name.
            # We can try to guess from the page title or just use "Current"
            # For now, let's skip if no seasons found to be safe, or try to parse the current page as "Current"
            pass
            
        for season_info in seasons:
            print(f"  Season: {season_info['name']}")
            
            # Get or create Season
            season = db.query(Season).filter_by(name=season_info['name']).first()
            if not season:
                season = Season(name=season_info['name'])
                db.add(season)
                db.commit()
                db.refresh(season)
                
            # Fetch standings
            soup = get_soup(season_info['url'])
            if not soup:
                continue
                
            data = parse_standings(soup)
            print(f"    Found {len(data)} teams.")
            
            for entry in data:
                team_name = entry['team']
                
                # Community mapping
                comm_name = normalize_community_name(team_name, community_map)
                
                # Get or create Community
                community = db.query(Community).filter_by(name=comm_name).first()
                if not community:
                    community = Community(name=comm_name)
                    db.add(community)
                    db.commit()
                    db.refresh(community)
                
                # Get or create Team
                team = db.query(Team).filter_by(name=team_name).first()
                if not team:
                    team = Team(name=team_name, community_id=community.id)
                    db.add(team)
                    db.commit()
                    db.refresh(team)
                elif team.community_id != community.id:
                    # Update community if changed (e.g. mapping updated)
                    team.community_id = community.id
                    db.commit()
                    
                # Update or Insert Standing
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
                
                # Update stats
                standing.gp = entry['gp']
                standing.w = entry['w']
                standing.l = entry['l']
                standing.t = entry['t']
                standing.pts = entry['pts']
                standing.gf = entry['gf']
                standing.ga = entry['ga']
                standing.diff = entry['diff']
                
                db.commit()
                
    db.close()
    print("Sync complete.")

if __name__ == "__main__":
    sync_data()
