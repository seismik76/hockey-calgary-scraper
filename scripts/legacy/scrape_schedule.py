import requests
from bs4 import BeautifulSoup
import pandas as pd
import urllib3
import time
import random
import re

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://www.hockeycalgary.ca"
START_URL = "https://www.hockeycalgary.ca/schedule/full/league/380/"

def get_session():
    session = requests.Session()
    session.verify = False
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    return session

def get_league_links(session):
    print(f"Fetching league directory from {START_URL}...")
    try:
        response = session.get(START_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all links that look like schedule streams
        # Pattern: /schedule/upcoming/stream/... or /schedule/full/stream/...
        links = []
        seen_urls = set()
        
        # The directory page usually has a table with links
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/schedule/upcoming/stream/' in href:
                full_url = BASE_URL + href if href.startswith('/') else href
                if full_url not in seen_urls:
                    links.append({
                        'name': a.get_text(strip=True),
                        'url': full_url
                    })
                    seen_urls.add(full_url)
        
        print(f"Found {len(links)} league links.")
        return links
    except Exception as e:
        print(f"Error fetching league directory: {e}")
        return []

def scrape_games(session, league_name, url):
    print(f"Scraping schedule for {league_name}...")
    games = []
    try:
        response = session.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the games table
        table = soup.find('table', class_='games-table')
        if not table:
            print(f"No games table found for {league_name}")
            return []
        
        # Parse rows
        rows = table.find('tbody').find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 8:
                continue
                
            # Extract data based on the structure seen in schedule_known.html
            # Date, Time, (Calendar), Arena, Home, Visitor, Type, Game #
            
            date = cols[0].get_text(strip=True)
            time_str = cols[1].get_text(strip=True)
            # col 2 is calendar icon
            arena = cols[3].get_text(strip=True)
            home = cols[4].get_text(strip=True)
            visitor = cols[5].get_text(strip=True)
            game_type = cols[6].get_text(strip=True)
            game_num = cols[7].get_text(strip=True)
            
            games.append({
                'League': league_name,
                'Date': date,
                'Time': time_str,
                'Arena': arena,
                'Home': home,
                'Visitor': visitor,
                'Type': game_type,
                'Game Number': game_num,
                'Source URL': url
            })
            
        print(f"Found {len(games)} games for {league_name}")
        return games
        
    except Exception as e:
        print(f"Error scraping {league_name}: {e}")
        return []

def main():
    session = get_session()
    
    # 1. Get all league links
    league_links = get_league_links(session)
    
    if not league_links:
        print("No leagues found. Exiting.")
        return

    all_games = []
    
    # Scrape all leagues
    leagues_to_scrape = league_links
    
    print(f"Scraping {len(leagues_to_scrape)} leagues...")
    
    for league in leagues_to_scrape:
        games = scrape_games(session, league['name'], league['url'])
        all_games.extend(games)
        time.sleep(1) # Be polite
        
    if all_games:
        df = pd.DataFrame(all_games)
        print("\nScraped Data Sample:")
        print(df.head())
        
        filename = 'hockey_calgary_schedule.csv'
        df.to_csv(filename, index=False)
        print(f"\nSaved {len(all_games)} games to {filename}")
    else:
        print("No games scraped.")

if __name__ == "__main__":
    main()
