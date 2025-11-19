import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def inspect_schedule_search_types():
    url = 'https://www.hockeycalgary.ca/schedule/search'
    print(f'Fetching {url}...')
    try:
        response = requests.get(url, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        selects = soup.find_all('select')
        for select in selects:
            name = select.get('name')
            if name == 'type':
                print(f'\nFound Select: {name}')
                options = select.find_all('option')
                for option in options:
                    value = option.get('value')
                    text = option.get_text(strip=True)
                    print(f'  Type ID: {value} -> {text}')

    except Exception as e:
        print(f'Error: {e}')

if __name__ == '__main__':
    inspect_schedule_search_types()
