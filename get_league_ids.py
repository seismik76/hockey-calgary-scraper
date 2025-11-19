import requests
from bs4 import BeautifulSoup
import urllib3
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://www.hockeycalgary.ca/schedule/search"

try:
    response = requests.get(url, verify=False)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    
    league_map = {}
    
    # Find the league select
    # It might be populated via AJAX? Let's check the static HTML first.
    select = soup.find('select', {'name': 'league'})
    if select:
        for option in select.find_all('option'):
            value = option.get('value')
            text = option.get_text(strip=True)
            if value:
                league_map[text] = value
                
    print(f"Found {len(league_map)} leagues in dropdown.")
    # print(json.dumps(league_map, indent=2))
    
    # Check if U11 Tier 1 is there
    if "U11 Tier 1" in league_map:
        print(f"U11 Tier 1 ID: {league_map['U11 Tier 1']}")
    else:
        print("U11 Tier 1 not found in dropdown (might be dynamic).")

except Exception as e:
    print(f"Error: {e}")
