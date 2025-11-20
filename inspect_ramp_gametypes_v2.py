import requests
from bs4 import BeautifulSoup

def inspect_ramp_gametypes():
    # A sample U11 league URL (RAMP)
    # We need a valid URL. Based on scraper.py, it scrapes from the main page.
    # Let's try to find a valid league URL first.
    
    base_url = "http://hockeycalgary.msa4.rampinteractive.com/"
    response = requests.get(base_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    standings_links = soup.find_all('a', string=lambda t: t and 'Standings' in t)
    
    if not standings_links:
        print("No standings links found on main page.")
        return

    # Pick the first one
    first_link = standings_links[0]['href']
    full_url = f"http://hockeycalgary.msa4.rampinteractive.com{first_link}"
    print(f"Inspecting URL: {full_url}")
    
    resp = requests.get(full_url)
    soup = BeautifulSoup(resp.content, 'html.parser')
    
    gt_select = soup.find('select', id='ddlGameType')
    if gt_select:
        print("\nGame Types found:")
        for opt in gt_select.find_all('option'):
            val = opt.get('value')
            text = opt.get_text(strip=True)
            print(f"  ID: {val}, Name: '{text}'")
    else:
        print("No ddlGameType select found.")

    # Check Seasons
    season_select = soup.find('select', id='ddlSeason')
    if season_select:
        print("\nSeasons found:")
        for opt in season_select.find_all('option'):
            val = opt.get('value')
            text = opt.get_text(strip=True)
            print(f"  ID: {val}, Name: '{text}'")
            
            # If it's a past season, let's inspect its game types too
            if text != "2025-2026":
                # We need to fetch the page with this season selected. 
                # RAMP usually reloads the page or uses JS. 
                # The URL structure might not change, but the content depends on the POST or query param?
                # Actually, looking at scraper.py, it uses the API with the season ID.
                # But to see the game types *names*, we might need to load the page or guess.
                pass
    else:
        print("No ddlSeason select found.")

if __name__ == "__main__":
    inspect_ramp_gametypes()
