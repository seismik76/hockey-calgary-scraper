import requests
from bs4 import BeautifulSoup
import urllib3
import time
import json
from scraper import get_leagues, get_soup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://www.hockeycalgary.ca"

def get_teams_from_league(league_url):
    soup = get_soup(league_url)
    if not soup:
        return []
    
    teams = []
    # Find the standings table
    table = soup.find('table')
    if table:
        links = table.find_all('a', href=True)
        for link in links:
            if "/team/" in link['href']:
                teams.append({
                    'name': link.get_text(strip=True),
                    'url': f"{BASE_URL}{link['href']}"
                })
    return teams

def get_seeding_games(team_url):
    soup = get_soup(team_url)
    if not soup:
        return []
    
    games = []
    tables = soup.find_all('table')
    for table in tables:
        headers = [th.get_text(strip=True) for th in table.find_all('th')]
        if 'Type' in headers and 'Score' in headers:
            header_map = {h: i for i, h in enumerate(headers)}
            
            rows = table.find_all('tr')
            for row in rows[1:]:
                cols = row.find_all('td')
                if not cols: continue
                
                try:
                    game_type = cols[header_map['Type']].get_text(strip=True)
                    if game_type == 'Seeding':
                        date = cols[header_map['Date']].get_text(strip=True)
                        home = cols[header_map['Home']].get_text(strip=True)
                        score = cols[header_map['Score']].get_text(strip=True)
                        away = cols[header_map['Away']].get_text(strip=True)
                        
                        games.append({
                            'date': date,
                            'home': home,
                            'score': score,
                            'away': away,
                            'type': game_type
                        })
                except (IndexError, KeyError):
                    continue
            # Once we found the schedule table, we can stop looking at other tables
            # unless there are multiple schedule tables? Usually just one.
            break
            
    return games

def main():
    print("Fetching leagues...")
    leagues = get_leagues()
    
    # Filter for U11 Tier 1 for testing
    target_league = next((l for l in leagues if l['name'] == 'U11 Tier 1'), None)
    
    if not target_league:
        print("U11 Tier 1 not found.")
        return

    # Force 2024-2025 season for testing
    league_url = f"{target_league['url']}/season/2024-2025"

    print(f"Processing {target_league['name']}...")
    print(f"URL: {league_url}")
    teams = get_teams_from_league(league_url)
    print(f"Found {len(teams)} teams.")
    
    all_seeding_games = []
    
    for team in teams:
        print(f"  Scraping {team['name']}...")
        games = get_seeding_games(team['url'])
        if games:
            print(f"    Found {len(games)} seeding games.")
            all_seeding_games.extend(games)
        else:
            print("    No seeding games found.")
        
        # Be nice to the server
        time.sleep(1)
        
    print(f"Total seeding games found: {len(all_seeding_games)}")
    
    # Deduplicate games (since we scrape both home and away teams)
    # A simple way is to use a set of tuples (date, home, away)
    unique_games = {}
    for game in all_seeding_games:
        key = (game['date'], game['home'], game['away'])
        if key not in unique_games:
            unique_games[key] = game
            
    print(f"Unique seeding games: {len(unique_games)}")
    
    # Save to file
    with open('seeding_games.json', 'w') as f:
        json.dump(list(unique_games.values()), f, indent=2)
    print("Saved to seeding_games.json")

if __name__ == "__main__":
    main()
