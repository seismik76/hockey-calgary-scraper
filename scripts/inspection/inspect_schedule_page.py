import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://www.hockeycalgary.ca/schedule/full/league/u11-tier-1"

try:
    response = requests.get(url, verify=False)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Look for a table of games
    tables = soup.find_all('table')
    print(f"Found {len(tables)} tables.")
    
    for i, table in enumerate(tables):
        headers = [th.get_text(strip=True) for th in table.find_all('th')]
        print(f"Table {i} Headers: {headers}")
        
        # Print first few rows
        rows = table.find_all('tr')
        for j, row in enumerate(rows[:5]):
            cols = [td.get_text(strip=True) for td in row.find_all('td')]
            if cols:
                print(f"  Row {j}: {cols}")

except Exception as e:
    print(f"Error: {e}")
