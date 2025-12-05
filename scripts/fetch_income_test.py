import requests
from bs4 import BeautifulSoup

def fetch_profile():
    url = "https://www.calgary.ca/communities/profiles/tuscany.html"
    try:
        response = requests.get(url)
        print(f"Status: {response.status_code}")
        # print(response.text[:1000])
        
        soup = BeautifulSoup(response.text, 'html.parser')
        # Search for income related text
        text = soup.get_text()
        if "135,061" in text or "135061" in text:
            print("Found income in text!")
        else:
            print("Income not found in text.")
            
        # Look for links to PDFs
        for a in soup.find_all('a'):
            if 'pdf' in a.get('href', ''):
                print(f"PDF Link: {a['href']}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fetch_profile()
