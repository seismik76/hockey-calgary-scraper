import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def inspect_ramp_names():
    url = "http://hockeycalgary.msa4.rampinteractive.com/"
    print(f"Fetching {url}...")
    try:
        response = requests.get(url, verify=False)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        standings_links = soup.find_all('a', string=lambda t: t and 'Standings' in t)
        
        for a in standings_links:
            href = a['href']
            # Traverse up to find a header
            parent = a.parent
            found_name = None
            
            # Go up 5 levels max
            curr = parent
            for _ in range(5):
                if not curr: break
                
                # Check previous siblings for headers
                prev = curr.find_previous_sibling(['h1', 'h2', 'h3', 'h4', 'h5', 'div'])
                if prev:
                    # Check if it looks like a name
                    text = prev.get_text(strip=True)
                    if text and len(text) < 50 and 'Games' not in text:
                        found_name = text
                        break
                
                # Also check if the parent itself has a class that might indicate a name
                # or if it contains a header
                header = curr.find(['h1', 'h2', 'h3', 'h4', 'h5'])
                if header:
                     text = header.get_text(strip=True)
                     if text:
                         found_name = text
                         break
                         
                curr = curr.parent
            
            print(f"Link: {href} -> Name: {found_name or 'Unknown'}")

    except Exception as e:
        print(f"Error: {e}")

def inspect_teamlinkt_params():
    # Try to fetch a specific league
    # Value from previous run: U13 TIER 1 NORTH -> 249020-249130
    url = "https://leagues.teamlinkt.com/hockeycalgary/Standings"
    params = {
        'hierarchy_filter': '249020-249130'
    }
    print(f"\nFetching {url} with params {params}...")
    try:
        response = requests.get(url, params=params, verify=False)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check if we got a table
        table = soup.find('table')
        if table:
            print("Found a table!")
            headers = [th.get_text(strip=True) for th in table.find_all('th')]
            print(f"Headers: {headers}")
            
            rows = table.find_all('tr')
            if len(rows) > 1:
                cols = [td.get_text(strip=True) for td in rows[1].find_all('td')]
                print(f"Row 1: {cols}")
        else:
            print("No table found with params.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_ramp_names()
    inspect_teamlinkt_params()