import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://www.hockeycalgary.ca/standings/index/stream/community-council/league/u11-tier-1/season/2023-2024"

try:
    response = requests.get(url, verify=False)
    with open("u11_tier1.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    print("Saved HTML to u11_tier1.html")

except Exception as e:
    print(f"Error: {e}")
