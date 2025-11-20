from scraper import get_seasons_for_league

url = "https://www.hockeycalgary.ca/standings/index/stream/community-council/league/u11-tier-1"
seasons = get_seasons_for_league(url)
print(f"Seasons for {url}:")
for s in seasons:
    print(f"  {s['name']} ({s['slug']})")
