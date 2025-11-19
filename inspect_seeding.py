import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Target a specific league page
url = "https://www.hockeycalgary.ca/standings/index/stream/community-council/league/u11-tier-1/season/2023-2024"

try:
    response = requests.get(url, verify=False)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    
    print(f"Page Title: {soup.title.string}")
    
    # Search for the word "Seeding" anywhere in the text
    if "Seeding" in soup.get_text():
        print("Found 'Seeding' in page text!")
    else:
        print("'Seeding' not found in page text.")

    # Look for all links and print those containing 'seed'
    print("\nLinks containing 'seed':")
    for a in soup.find_all('a', href=True):
        if 'seed' in a['href'].lower() or 'seed' in a.get_text(strip=True).lower():
            print(f"Text: {a.get_text(strip=True)}, Href: {a['href']}")

    # Look for forms/selects again to see if we missed a "Phase" selector
    print("\nSelect options:")
    for select in soup.find_all('select'):
        print(f"Select Name: {select.get('name')}")
        for option in select.find_all('option'):
            print(f"  Option: {option.get_text(strip=True)}, Value: {option.get('value')}")

except Exception as e:
    print(f"Error: {e}")
