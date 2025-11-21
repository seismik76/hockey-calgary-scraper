import requests

url = "https://www.hockeycalgary.ca/tournament/content/season/2025-2026/tournament/esso-minor-hockey-week/page/home"
resp = requests.get(url, verify=False)
with open("esso_dump.html", "w", encoding="utf-8") as f:
    f.write(resp.text)
print("Saved esso_dump.html")
