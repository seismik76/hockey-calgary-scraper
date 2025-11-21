import requests
from bs4 import BeautifulSoup

url = "https://www.hockeycalgary.ca/tournament/content/season/2023-2024/tournament/city-championships/page/home"
print(f"Fetching {url}")
resp = requests.get(url, verify=False)
soup = BeautifulSoup(resp.content, 'html.parser')

print("Links found:")
for a in soup.find_all('a', href=True):
    href = a['href']
    if '/league/' in href:
        print(f"  {a.get_text(strip=True)} -> {href}")
