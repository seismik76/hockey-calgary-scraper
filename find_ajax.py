import requests
from bs4 import BeautifulSoup
import urllib3
import re

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://www.hockeycalgary.ca/schedule/search"

try:
    response = requests.get(url, verify=False)
    html = response.text
    
    # Look for AJAX URLs
    print("Potential AJAX URLs:")
    urls = re.findall(r'[\'"](/[^\'"]*ajax[^\'"]*)[\'"]', html, re.IGNORECASE)
    for u in urls:
        print(u)
        
    # Look for any script that mentions "league" or "team"
    # print("\nScripts:")
    # soup = BeautifulSoup(html, 'html.parser')
    # for script in soup.find_all('script'):
    #    if script.string and ('league' in script.string or 'team' in script.string):
    #        print(script.string[:200]) # Print first 200 chars

except Exception as e:
    print(f"Error: {e}")
