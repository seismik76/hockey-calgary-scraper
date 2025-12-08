import requests
import pdfplumber
import io
import re

def test_eagle_ridge_logic():
    url = "https://www.calgary.ca/content/dam/www/programs-services/property-housing-and-neighbourhoods/neighbourhood-and-community-relationships/profiles/eagle-ridge.pdf"
    print(f"Fetching {url}...")
    
    response = requests.get(url)
    f = io.BytesIO(response.content)
    
    with pdfplumber.open(f) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"
            
    print("Text extracted. Running logic...")
    
    phrases = [
        "Median household income of private households",
        "Median total household income (before tax) in 2020",
        "Median total income of households",
        "Median total income in 2020",
        "Median total income"
    ]
    
    data = {}
    
    for phrase in phrases:
        inc_idx = full_text.find(phrase)
        if inc_idx != -1:
            print(f"Found phrase: '{phrase}'")
            # Look at the next 400 chars
            snippet = full_text[inc_idx:inc_idx+400]
            print(f"Snippet: {snippet[:100]}...")
            
            numbers = re.findall(r'[\$\s]([\d,]{3,})', snippet)
            found_income = False
            for num in numbers:
                try:
                    val = int(num.replace(',', ''))
                    # Filter out range boundaries (e.g. 39,999, 59,999)
                    if val % 10000 == 9999:
                        continue
                        
                    # 40k to 1M is reasonable range for median income
                    # Eagle Ridge is > 400k
                    if 40000 < val < 1000000: 
                        print(f"Found Value: {val}")
                        data['median_income'] = val
                        found_income = True
                        break
                except:
                    continue
            if found_income:
                break
                
    print(f"Final Result: {data.get('median_income')}")

if __name__ == "__main__":
    test_eagle_ridge_logic()
