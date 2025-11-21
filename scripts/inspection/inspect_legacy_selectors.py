import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://www.hockeycalgary.ca/standings/index/stream/community-council/league/u13-tier-3-south"

try:
    response = requests.get(url, verify=False)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    print(f"Title: {soup.title.string if soup.title else 'No Title'}")
    
    print("\nSelectors:")
    selects = soup.find_all('select')
    for select in selects:
        name = select.get('name') or select.get('id') or "Unnamed"
        print(f"  Select: {name}")
        for option in select.find_all('option'):
            print(f"    Option: {option.get_text(strip=True)} -> {option.get('value')}")

    print("\nLinks with 'type' in href:")
    for a in soup.find_all('a', href=True):
        if '/type/' in a['href']:
            print(f"  {a.get_text(strip=True)} -> {a['href']}")

except Exception as e:
    print(f"Error: {e}")
