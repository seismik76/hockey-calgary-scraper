import requests
import pdfplumber
import io
import re

def inspect_eagle_ridge():
    url = "https://www.calgary.ca/content/dam/www/programs-services/property-housing-and-neighbourhoods/neighbourhood-and-community-relationships/profiles/eagle-ridge.pdf"
    print(f"Fetching {url}...")
    
    response = requests.get(url)
    f = io.BytesIO(response.content)
    
    with pdfplumber.open(f) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if "Median total income" in text or "432,000" in text:
                print(f"--- Page {i+1} ---")
                print(text)
                print("-" * 20)

if __name__ == "__main__":
    inspect_eagle_ridge()
