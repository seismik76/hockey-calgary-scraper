import requests
from bs4 import BeautifulSoup

url = "https://www.hockeycalgary.ca/tournament/brackets/season/2024-2025/tournament/esso-minor-hockey-week/page/home/category/u11/league/u11-aa"
resp = requests.get(url, verify=False)
soup = BeautifulSoup(resp.content, 'html.parser')

print("Links on tournament league page:")
for a in soup.find_all('a', href=True):
    text = a.get_text(strip=True)
    href = a['href']
    if 'standings' in href or 'Standings' in text:
        print(f"  {text} -> {href}")
