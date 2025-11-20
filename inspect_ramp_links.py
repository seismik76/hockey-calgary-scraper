import requests
from bs4 import BeautifulSoup

def list_ramp_links():
    url = "http://hockeycalgary.msa4.rampinteractive.com/"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    print("Links found on RAMP main page:")
    for a in soup.find_all('a', href=True):
        text = a.get_text(strip=True)
        href = a['href']
        if 'division' in href or 'tournament' in href or 'Esso' in text:
            print(f"  Text: {text}, Href: {href}")

if __name__ == "__main__":
    list_ramp_links()
