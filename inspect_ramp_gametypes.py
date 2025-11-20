import requests
from bs4 import BeautifulSoup

def get_soup(url):
    try:
        response = requests.get(url)
        return BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def inspect_gametypes(url):
    print(f"Inspecting {url}...")
    soup = get_soup(url)
    if not soup: return

    select = soup.find('select', id='ddlGameType')
    if select:
        print("Found ddlGameType:")
        for opt in select.find_all('option'):
            print(f"  - {opt.get_text(strip=True)}: {opt.get('value')}")
    else:
        print("No ddlGameType found.")

if __name__ == "__main__":
    # URL from screenshot (approximate, using the IDs)
    # http://hockeycalgary.msa4.rampinteractive.com/division/3300/30087/standings
    url1 = "http://hockeycalgary.msa4.rampinteractive.com/division/3300/30087/standings"
    inspect_gametypes(url1)
    
    # Try another one to see if IDs change
    # From previous output: /division/3300/30084/standings
    url2 = "http://hockeycalgary.msa4.rampinteractive.com/division/3300/30084/standings"
    inspect_gametypes(url2)
