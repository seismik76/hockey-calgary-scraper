import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from scraper import get_leagues, get_soup, parse_standings, get_seasons_for_league
from utilities.utils import normalize_community_name, load_community_map

def debug_legacy_scraping():
    year = "2023-2024"
    print(f"Fetching leagues for {year}...")
    leagues = get_leagues(year)
    
    # Find a U11 league
    u11_league = next((l for l in leagues if "U11" in l['name']), None)
    
    if not u11_league:
        print("No U11 league found.")
        return
        
    print(f"Testing with {u11_league['name']} ({u11_league['url']})...")
    
    print("Fetching available seasons for this league...")
    seasons = get_seasons_for_league(u11_league['url'])
    print(f"Found {len(seasons)} seasons.")
    
    target_season = next((s for s in seasons if "2023-2024" in s['name']), None)
    
    if target_season:
        print(f"Found target season: {target_season['name']} -> {target_season['url']}")
        soup = get_soup(target_season['url'])
        data = parse_standings(soup)
        print(f"Found {len(data)} standings records.")
        
        community_map = load_community_map()
        for entry in data:
            team_name = entry['team']
            norm_name = normalize_community_name(team_name, community_map)
            print(f"  Team: '{team_name}' -> Normalized: '{norm_name}'")
    else:
        print("Target season 2023-2024 not found in dropdown.")
        for s in seasons:
            print(f"  - {s['name']}")

if __name__ == "__main__":
    debug_legacy_scraping()
