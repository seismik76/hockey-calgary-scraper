import requests
from bs4 import BeautifulSoup
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def inspect_mhr():
    # Inspect a specific team page
    url = "https://v5.myhockeyrankings.com/team-info?t=3630&y=2023"
    print(f"Fetching {url}...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        resp = requests.get(url, headers=headers, verify=False)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Dump all inline scripts to a file
        with open('scripts_dump.txt', 'w', encoding='utf-8') as f:
            for s in soup.find_all('script'):
                if s.string:
                    f.write("--- SCRIPT START ---\n")
                    f.write(s.string)
                    f.write("\n--- SCRIPT END ---\n")
        print("Dumped scripts to scripts_dump.txt")

                    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_mhr()
