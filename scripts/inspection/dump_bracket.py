import requests

url = "https://www.hockeycalgary.ca/tournament/brackets/season/2024-2025/tournament/esso-minor-hockey-week/page/home/category/u11/league/u11-aa"
resp = requests.get(url, verify=False)
with open("bracket_dump.html", "w", encoding="utf-8") as f:
    f.write(resp.text)
print("Saved bracket_dump.html")
