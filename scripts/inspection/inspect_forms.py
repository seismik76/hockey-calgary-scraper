import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://www.hockeycalgary.ca/standings/index/stream/community-council/league/u11-tier-1/season/2023-2024"

try:
    response = requests.get(url, verify=False)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    print("Forms:")
    for form in soup.find_all('form'):
        print(f"Action: {form.get('action')}")
        for input_tag in form.find_all('input'):
            print(f"  Input: {input_tag.get('name')} = {input_tag.get('value')}")
        for select in form.find_all('select'):
            print(f"  Select: {select.get('name')}")

except Exception as e:
    print(f"Error: {e}")
