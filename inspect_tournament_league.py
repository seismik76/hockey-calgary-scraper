import requests
from bs4 import BeautifulSoup

url = "https://www.hockeycalgary.ca/tournament/brackets/season/2024-2025/tournament/esso-minor-hockey-week/page/home/category/u11/league/u11-aa"
print(f"Fetching {url}")
resp = requests.get(url, verify=False)
soup = BeautifulSoup(resp.content, 'html.parser')

tables = soup.find_all('table')
print(f"Found {len(tables)} tables.")

for i, t in enumerate(tables):
    headers = [th.get_text(strip=True) for th in t.find_all('th')]
    print(f"Table {i} headers: {headers}")
