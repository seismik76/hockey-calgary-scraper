import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def inspect_seeding_schedule(category_id, league_id):
    url = 'https://www.hockeycalgary.ca/schedule/search/'
    params = {
        'search': 'yes',
        'category': category_id,
        'league': league_id,
        'team': '',
        'type': '5', # Seeding
        'association': '0',
        'arena': ''
    }
    
    print(f'Fetching {url} with params {params}...')
    
    session = requests.Session()
    session.verify = False
    
    try:
        # Visit the page first to get cookies
        session.get('https://www.hockeycalgary.ca/schedule/search')
        
        # Now perform the search
        response = session.get(url, params=params)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        tables = soup.find_all('table')
        print(f'Found {len(tables)} tables.')
        
        for i, table in enumerate(tables):
            rows = table.find_all('tr')
            print(f'Table {i+1} has {len(rows)} rows.')
            if len(rows) > 0:
                headers = [th.get_text(strip=True) for th in rows[0].find_all(['th', 'td'])]
                print(f'  Headers: {headers}')
                for row in rows[1:5]:
                    cols = [td.get_text(strip=True) for td in row.find_all('td')]
                    print(f'  Row: {cols}')

    except Exception as e:
        print(f'Error: {e}')

if __name__ == '__main__':
    # U11 Tier 1 North (380)
    inspect_seeding_schedule(15, 380)
