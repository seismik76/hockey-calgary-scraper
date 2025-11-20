import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def check_legacy_u11(year):
    url = f"https://www.hockeycalgary.ca/standings/index/season/{year}"
    print(f"Checking {url}...")
    try:
        resp = requests.get(url, verify=False)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        text = soup.get_text()
        if "U11" in text:
            print(f"  Found 'U11' in text for {year}!")
            # Find specific links
            links = soup.find_all('a', href=True)
            # Look for actual league links, not just category headers
            league_links = [l for l in links if '/league/' in l['href']]
            print(f"  Found {len(league_links)} league links.")
            if league_links:
                print(f"  Sample: {league_links[0].get_text()} -> {league_links[0]['href']}")
        else:
            print(f"  'U11' NOT found for {year}.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_legacy_u11("2023-2024")
    check_legacy_u11("2022-2023")
