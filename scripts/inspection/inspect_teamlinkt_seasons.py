import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://leagues.teamlinkt.com/hockeycalgary/Standings"
response = requests.get(url, verify=False)
soup = BeautifulSoup(response.content, 'html.parser')

print("Season ID Options:")
select = soup.find('select', {'id': 'season_id'})
if select:
    for opt in select.find_all('option'):
        print(f"  {opt.get_text(strip=True)} -> {opt.get('value')} (Selected: {opt.get('selected')})")
else:
    print("No season_id select found.")
