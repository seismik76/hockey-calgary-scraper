import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Example URL for City Championships (Playoffs) - Specific League
url = "https://www.hockeycalgary.ca/tournament/brackets/season/2023-2024/tournament/city-championships/page/home/category/u11/league/u11-tier-1-north"

try:
    response = requests.get(url, verify=False)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    
    print(f"Title: {soup.title.string}")
    
    # Look for tables
    tables = soup.find_all('table')
    print(f"Found {len(tables)} tables.")
    for i, table in enumerate(tables):
        print(f"Table {i}:")
        headers = [th.get_text(strip=True) for th in table.find_all('th')]
        print(f"  Headers: {headers}")
        rows = table.find_all('tr')
        if len(rows) > 1:
            first_row_cols = [td.get_text(strip=True) for td in rows[1].find_all('td')]
            print(f"  First row: {first_row_cols}")

except Exception as e:
    print(f"Error: {e}")
