import requests
import urllib3

# Suppress InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://www.hockeycalgary.ca/schedule/search/"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

session = requests.Session()

print(f"Fetching {url} (no params)...")
try:
    response = session.get(url, headers=headers, verify=False)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Successfully fetched search page.")
    else:
        print("Failed to fetch search page.")
except Exception as e:
    print(f"Error: {e}")

# Now try with params
params = {
    'search': 'yes',
    'category': '15',
    'league': '380',
    'team': '',
    'type': '5',
    'association': '0',
    'arena': '',
    'start': '',
    'end': '',
    'game_number': ''
}

print(f"\nFetching {url} with params...")
try:
    response = session.get(url, headers=headers, params=params, verify=False)
    print(f"Status Code: {response.status_code}")
    print(f"URL: {response.url}")
    if response.status_code == 200:
        print("Successfully fetched schedule.")
        print(response.text[:500])
    else:
        print("Failed to fetch schedule.")
except Exception as e:
    print(f"Error: {e}")

# Test 1: Just category
params_1 = {
    'search': 'yes',
    'category': '15',
}
print(f"\nTest 1: Fetching with category=15...")
try:
    response = session.get(url, headers=headers, params=params_1, verify=False)
    print(f"Status Code: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")

# Test 2: Category + League
params_2 = {
    'search': 'yes',
    'category': '15',
    'league': '380',
}
print(f"\nTest 2: Fetching with category=15, league=380...")
try:
    response = session.get(url, headers=headers, params=params_2, verify=False)
    print(f"Status Code: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")

# Test 3: Category + League + Type
params_3 = {
    'search': 'yes',
    'category': '15',
    'league': '380',
    'type': '5',
}
print(f"\nTest 3: Fetching with category=15, league=380, type=5...")
try:
    response = session.get(url, headers=headers, params=params_3, verify=False)
    print(f"Status Code: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")

# Test 4: Category + League=0
params_4 = {
    'search': 'yes',
    'category': '15',
    'league': '0',
}
print(f"\nTest 4: Fetching with category=15, league=0...")
try:
    response = session.get(url, headers=headers, params=params_4, verify=False)
    print(f"Status Code: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")

# Test 5: Category + League=381
params_5 = {
    'search': 'yes',
    'category': '15',
    'league': '381',
}
print(f"\nTest 5: Fetching with category=15, league=381...")
try:
    response = session.get(url, headers=headers, params=params_5, verify=False)
    print(f"Status Code: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")

# Test 6: Pretty URL search
url_6 = "https://www.hockeycalgary.ca/schedule/search/league/380/"
print(f"\nTest 6: Fetching {url_6}...")
try:
    response = session.get(url_6, headers=headers, verify=False)
    print(f"Status Code: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")

# Test 7: Pretty URL full schedule
url_7 = "https://www.hockeycalgary.ca/schedule/full/league/380/"
print(f"\nTest 7: Fetching {url_7}...")
try:
    response = session.get(url_7, headers=headers, verify=False)
    print(f"Status Code: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")

# Test 8: Category + League + Dates
params_8 = {
    'search': 'yes',
    'category': '15',
    'league': '380',
    'start': '2023-10-01',
    'end': '2024-04-01',
}
print(f"\nTest 8: Fetching with category=15, league=380, dates...")
try:
    response = session.get(url, headers=headers, params=params_8, verify=False)
    print(f"Status Code: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")

# Test 9: Slug URL
url_9 = "https://www.hockeycalgary.ca/schedule/full/stream/community-council/league/u11-tier-1-north"
print(f"\nTest 9: Fetching {url_9}...")
try:
    response = session.get(url_9, headers=headers, verify=False)
    print(f"Status Code: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")

# Test 10: Known working slug URL
url_10 = "https://www.hockeycalgary.ca/schedule/upcoming/stream/community-council/league/u11-flames-nchl"
print(f"\nTest 10: Fetching {url_10}...")
try:
    response = session.get(url_10, headers=headers, verify=False)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        with open("schedule_known.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        print("Saved schedule to schedule_known.html")
except Exception as e:
    print(f"Error: {e}")
