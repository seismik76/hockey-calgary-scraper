import requests
from bs4 import BeautifulSoup

def inspect():
    # RAMP
    url = "http://hockeycalgary.msa4.rampinteractive.com/division/3300/30078/standings"
    print(f"Fetching {url}")
    resp = requests.get(url)
    with open("ramp_dump.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
    print("Saved ramp_dump.html")

    # TeamLinkt
    url = "https://leagues.teamlinkt.com/hockeycalgary/Standings?hierarchy_filter=249020-249021"
    print(f"Fetching {url}")
    resp = requests.get(url, verify=False)
    with open("teamlinkt_dump.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
    print("Saved teamlinkt_dump.html")

if __name__ == "__main__":
    inspect()