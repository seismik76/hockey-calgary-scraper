import requests
from bs4 import BeautifulSoup

def test_ramp_season(season_id):
    url = f"http://hockeycalgary.msa4.rampinteractive.com/?season={season_id}" # Guessing param
    print(f"Testing {url}...")
    try:
        resp = requests.get(url)
        soup = BeautifulSoup(resp.content, 'html.parser')
        # Check if we see "2023-2024" or similar in the text
        if "2023-2024" in soup.get_text():
            print("  Found '2023-2024' in text!")
        else:
            print("  Did not find expected season text.")
            
        # Look for league links
        links = soup.find_all('a', href=True)
        standings_links = [l['href'] for l in links if 'standings' in l['href']]
        print(f"  Found {len(standings_links)} standings links.")
        if len(standings_links) > 0:
            print(f"  Sample: {standings_links[0]}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # 10603 is 2023-2024
    test_ramp_season(10603)
