from scraper import get_teamlinkt_leagues
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

print("Fetching TeamLinkt leagues...")
leagues = get_teamlinkt_leagues()
print(f"Found {len(leagues)} leagues.")
for l in leagues:
    print(f"  {l['name']} -> {l['slug']}")
