from scraper import get_leagues

leagues = get_leagues()
print(f"Found {len(leagues)} legacy leagues.")
for l in leagues:
    print(f"  {l['name']} ({l['url']})")
