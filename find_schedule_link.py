import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://www.hockeycalgary.ca/standings/index/stream/community-council/league/u11-tier-1/season/2023-2024"

try:
    response = requests.get(url, verify=False)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    print("Links to Schedule:")
    for a in soup.find_all('a', href=True):
        if 'schedule' in a['href']:
            print(f"Href: {a['href']}, Text: {a.get_text(strip=True)}")

except Exception as e:
    print(f"Error: {e}")
