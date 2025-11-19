from scraper import get_leagues, get_seasons_for_league
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

print("Fetching leagues...")
leagues = get_leagues()
print(f"Found {len(leagues)} leagues.")

if leagues:
    first_league = leagues[0]
    print(f"Checking seasons for {first_league['name']} ({first_league['url']})...")
    seasons = get_seasons_for_league(first_league['url'])
    print(f"Found {len(seasons)} seasons:")
    for s in seasons:
        print(f"  - {s['name']} ({s['slug']})")
