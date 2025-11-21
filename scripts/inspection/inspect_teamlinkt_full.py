import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://leagues.teamlinkt.com/hockeycalgary/Standings"
response = requests.get(url, verify=False)
soup = BeautifulSoup(response.content, 'html.parser')

selects = soup.find_all('select')
for select in selects:
    name = select.get('name') or select.get('id') or "Unnamed"
    print(f"\nSelect: {name}")
    for opt in select.find_all('option'):
        print(f"  {opt.get_text(strip=True)} -> {opt.get('value')}")
