import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://www.hockeycalgary.ca/schedule/search"

try:
    response = requests.get(url, verify=False)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    
    print("Options in Schedule Search Dropdowns:")
    for select in soup.find_all('select'):
        print(f"Select Name: {select.get('name')}")
        for option in select.find_all('option'):
            text = option.get_text(strip=True)
            value = option.get('value')
            if 'seed' in text.lower():
                print(f"  FOUND SEEDING: {text} (Value: {value})")
            # Print a few samples just to see structure
            # if value and len(value) > 0:
            #    print(f"  {text} ({value})")

except Exception as e:
    print(f"Error: {e}")
