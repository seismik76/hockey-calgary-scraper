import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def fetch_leagues_via_ajax(category_id):
    base_url = 'https://www.hockeycalgary.ca/schedule/getdata/collect/league/'
    
    # Variation 1: Empty strings
    params1 = [
        f'category/{category_id}',
        'league/',
        'association/',
        'team/',
        'type/',
        'arena/'
    ]
    
    headers = {
        'X-Requested-With': 'XMLHttpRequest',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    for i, params in enumerate([params1]):
        full_url = base_url + '/'.join(params) + '/'
        print(f'\nAttempt {i+1}: Fetching {full_url}...')
        
        try:
            response = requests.get(full_url, headers=headers, verify=False)
            response.raise_for_status()
            if len(response.text.strip()) > 0:
                print('Response content found!')
                soup = BeautifulSoup(response.text, 'html.parser')
                options = soup.find_all('option')
                print(f'Found {len(options)} options:')
                for option in options:
                    val = option.get('value')
                    text = option.get_text(strip=True)
                    if val and val != '0':
                        print(f'  ID: {val} -> {text}')
                return # Success
            else:
                print('Empty response.')
                
        except Exception as e:
            print(f'Error: {e}')

if __name__ == '__main__':
    fetch_leagues_via_ajax(15) # U11
