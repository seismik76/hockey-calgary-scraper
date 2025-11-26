import requests
from bs4 import BeautifulSoup
import re

BASE_URL = "https://albertaonehockey.ca"

def get_soup(url):
    try:
        response = requests.get(url, verify=False)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def inspect_site():
    print(f"Inspecting {BASE_URL}...")
    soup = get_soup(BASE_URL)
    if not soup: return

    # Look for Season Dropdown
    season_select = soup.find('select', id='ddlSeason')
    if season_select:
        print("\nFound Season Dropdown:")
        for opt in season_select.find_all('option'):
            print(f"  {opt.get_text(strip=True)} (ID: {opt.get('value')})")
    else:
        print("\nNo Season Dropdown found on home page.")

    # Look for Division/Category links
    print("\nSearching for Division links...")
    # Try to find links with /division/
    links = soup.find_all('a', href=True)
    for a in links:
        href = a['href']
        if '/division/' in href:
            print(f"  Found division link: {a.get_text(strip=True)} -> {href}")

    # Check the specific URL provided by user to see if we can extract Season ID
    specific_url = "https://albertaonehockey.ca/division/3300/30084/standings"
    print(f"\nInspecting specific URL: {specific_url}")
    soup_spec = get_soup(specific_url)
    if soup_spec:
        season_select = soup_spec.find('select', id='ddlSeason')
        if season_select:
            print("  Found Season Dropdown on specific page:")
            for opt in season_select.find_all('option'):
                print(f"    {opt.get_text(strip=True)} (ID: {opt.get('value')})")
        
        # Check for other dropdowns
        for select in soup_spec.find_all('select'):
            if select.get('id') != 'ddlSeason':
                print(f"  Found other dropdown: {select.get('id')}")
                for opt in select.find_all('option')[:5]: # Print first 5
                    print(f"    {opt.get_text(strip=True)} (ID: {opt.get('value')})")

if __name__ == "__main__":
    inspect_site()
