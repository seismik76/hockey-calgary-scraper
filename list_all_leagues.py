import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://www.hockeycalgary.ca/standings"

try:
    response = requests.get(url, verify=False)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    
    print("All Links on Standings Page:")
    for a in soup.find_all('a', href=True):
        text = a.get_text(strip=True)
        href = a['href']
        # Filter for league links
        if '/league/' in href:
            print(f"League: {text} | Href: {href}")

except Exception as e:
    print(f"Error: {e}")
