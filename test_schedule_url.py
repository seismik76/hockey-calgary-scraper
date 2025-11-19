import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Try using slug in schedule URL
url = "https://www.hockeycalgary.ca/schedule/full/league/u11-tier-1"

try:
    response = requests.get(url, verify=False, allow_redirects=False)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("Success! Slug works.")
    elif response.status_code == 302:
        print(f"Redirected to: {response.headers['Location']}")
    else:
        print("Failed.")

except Exception as e:
    print(f"Error: {e}")
