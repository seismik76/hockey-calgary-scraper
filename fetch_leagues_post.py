import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def inspect_leagues_for_category(category_id):
    url = "https://www.hockeycalgary.ca/schedule/search"
    print(f"Fetching {url} with category={category_id}...")
    
    # Try POST request
    data = {
        'category': category_id
    }
    
    try:
        response = requests.post(url, data=data, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the league dropdown
        selects = soup.find_all('select')
        for select in selects:
            name = select.get('name')
            if name == 'league':
                print(f"\nFound Select: {name}")
                options = select.find_all('option')
                print(f"Found {len(options)} options for league:")
                for option in options:
                    value = option.get('value')
                    text = option.get_text(strip=True)
                    if value:
                        print(f"  League ID: {value} -> {text}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_leagues_for_category(15) # U11
