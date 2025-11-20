import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_soup(url):
    try:
        response = requests.get(url, verify=False)
        return BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def inspect_ramp():
    print("\n--- Inspecting RAMP (Deep Dive) ---")
    # Try a specific division page which usually has the context
    url = "http://hockeycalgary.msa4.rampinteractive.com/division/3300/30084/standings"
    soup = get_soup(url)
    if not soup: 
        print("Failed to fetch RAMP division page")
        return

    selects = soup.find_all('select')
    for s in selects:
        print(f"Found select: id={s.get('id')}, name={s.get('name')}")
        options = s.find_all('option')
        print(f"  Option count: {len(options)}")
        for opt in options:
            print(f"  - {opt.get_text(strip=True)} (value={opt.get('value')})")

def inspect_legacy_years():
    print("\n--- Inspecting Legacy Years ---")
    years = ["2023-2024", "2022-2023", "2021-2022", "2020-2021"]
    base_url = "https://www.hockeycalgary.ca/standings/index/season/"
    
    for year in years:
        url = f"{base_url}{year}"
        soup = get_soup(url)
        if soup:
            title = soup.title.string if soup.title else "No Title"
            # Check if we actually got a valid page (sometimes they redirect to home)
            if "Page Not Found" not in title and "Home" not in title:
                print(f"Found valid page for {year}: {title.strip()}")
                # Look for leagues
                leagues = soup.find_all('a', href=True)
                count = sum(1 for l in leagues if '/league/' in l['href'])
                print(f"  - Found {count} league links")
            else:
                print(f"No data for {year} (Redirect/404)")

if __name__ == "__main__":
    inspect_ramp()
    # inspect_teamlinkt() # Skip for now, focus on RAMP/Legacy
    inspect_legacy_years()
