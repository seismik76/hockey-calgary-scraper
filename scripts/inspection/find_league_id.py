import requests
from bs4 import BeautifulSoup
import urllib3
import re

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://www.hockeycalgary.ca/standings/index/stream/community-council/league/u11-tier-1/season/2023-2024"

try:
    response = requests.get(url, verify=False)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Look for links to "Schedule" or "Games"
    print("Searching for Schedule links...")
    for a in soup.find_all('a', href=True):
        if 'schedule' in a['href']:
            print(f"Schedule Link: {a['href']}")
            
    # Look for any numeric ID associated with the league
    # Often in javascript or hidden inputs
    print("\nSearching for IDs...")
    html = str(soup)
    # Pattern for league_id=123 or similar
    ids = re.findall(r'league_id["\']?\s*[:=]\s*["\']?(\d+)', html)
    if ids:
        print(f"Found League IDs: {ids}")

except Exception as e:
    print(f"Error: {e}")
