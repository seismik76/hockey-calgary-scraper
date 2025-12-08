import requests
from bs4 import BeautifulSoup
import pdfplumber
import io
import re
import json
import time
import concurrent.futures
import os

BASE_URL = "https://www.calgary.ca"
PROFILES_URL = "https://www.calgary.ca/communities/profiles.html"
OUTPUT_FILE = "data/reference/neighborhood_demographics.json"

def get_community_links():
    print(f"Fetching community list from {PROFILES_URL}...")
    response = requests.get(PROFILES_URL)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    links = {}
    # The links are usually in a list or grid.
    # We look for links that contain '/communities/profiles/' and end in .html
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/communities/profiles/' in href and href.endswith('.html'):
            name = a.get_text(strip=True)
            if not name: continue
            
            # Clean name
            name = name.replace('\u200b', '') # Zero width space
            
            full_url = href
            if not full_url.startswith('http'):
                full_url = BASE_URL + href
            
            # Avoid duplicates or "Back to top" links
            # "South Calgary" is a valid community, so we must allow it.
            if "ward" in name.lower():
                continue
            if "calgary" in name.lower() and name.lower() != "south calgary":
                continue
                
            links[name] = full_url
            
    print(f"Found {len(links)} communities.")
    return links

def scrape_community(name, url):
    try:
        # print(f"Scraping {name}...")
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find PDF link
        pdf_url = None
        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.get_text().lower()
            
            # Logic:
            # 1. Must be a PDF
            # 2. Must not be a population projection
            # 3. Should probably contain the community slug or be in the 'profiles' path
            if '.pdf' in href and 'population-projection' not in href and 'ward' not in href:
                # Check if it looks like a profile
                # Usually in /content/dam/.../profiles/name.pdf
                if '/profiles/' in href:
                    pdf_url = href
                    if not pdf_url.startswith('http'):
                        pdf_url = BASE_URL + pdf_url
                    break
        
        if not pdf_url:
            # Fallback: Look for any PDF that isn't population projection
            for a in soup.find_all('a', href=True):
                href = a['href']
                if '.pdf' in href and 'population-projection' not in href:
                     pdf_url = href
                     if not pdf_url.startswith('http'):
                        pdf_url = BASE_URL + pdf_url
                     break
                     
        if not pdf_url:
            print(f"No PDF found for {name}")
            return None
            
        # Use a session for connection pooling
        session = requests.Session()
        
        # Download PDF
        pdf_response = session.get(pdf_url, timeout=15)
        f = io.BytesIO(pdf_response.content)
        
        data = {
            "name": name,
            "url": url,
            "pdf_url": pdf_url,
            "population": None,
            "median_income": None,
            "low_income_pct": None,
            "indigenous_identity": None,
            "immigrants": None,
            "age_gender_breakdown": []
        }
        
        with pdfplumber.open(f) as pdf:
            full_text = ""
            
            for page in pdf.pages:
                # Extract text once per page
                p_text = page.extract_text()
                if not p_text: continue
                
                full_text += p_text + "\n"
                
                # Check if we need tables from this page
                # We only extract tables if relevant keywords are found to save time
                keywords = [
                    "Number of Persons by Age and Gender",
                    "Median Household and Individual Income",
                    "Indigenous Identity", 
                    "Indigenous identity",
                    "Immigrants"
                ]
                
                if any(k in p_text for k in keywords):
                    tables = page.extract_tables()
                    
                    for table in tables:
                        if not table or len(table) < 2: continue
                        
                        # Check Header (Row 0 or 1)
                        # Row 0 is often "Calgary" or Community Name
                        # We need to be careful not to skip the community table if it has "Calgary" in the header row for comparison
                        # Usually the structure is:
                        # Row 0: [Community Name, Calgary] OR [Header1, Header2]
                        
                        # Let's identify the table type by its content or headers
                        
                        # Flatten first few rows for keyword search
                        header_rows = []
                        for r in table[:3]:
                            header_rows.extend([str(x).replace('\n', ' ').strip() for x in r if x])
                        header_str = " ".join(header_rows)
                        
                        # --- Age / Gender Table ---
                        if "Total" in header_str and "Men" in header_str and "Women" in header_str and "0-4" in str(table):
                            # Check if this is the Calgary table (usually has "Calgary" in first row/cell)
                            if "Calgary" in str(table[0]):
                                continue
                                
                            for row in table[2:]:
                                clean_row = [str(x).replace('\n', ' ').strip() for x in row if x]
                                if not clean_row: continue
                                
                                age_group = clean_row[0]
                                if "Population" in age_group: continue
                                
                                if len(clean_row) >= 4:
                                    try:
                                        total = int(clean_row[1].replace(',', ''))
                                        men = int(clean_row[2].replace(',', ''))
                                        women = int(clean_row[3].replace(',', ''))
                                        data['age_gender_breakdown'].append({
                                            "age_group": age_group,
                                            "total": total,
                                            "men": men,
                                            "women": women
                                        })
                                    except ValueError:
                                        continue

                        # --- Income Table ---
                        elif "Median household income" in str(table) or "Median Household and Individual Income" in p_text:
                             # Check for specific row
                            for row in table:
                                clean_row = [str(x).replace('\n', ' ').strip() for x in row if x]
                                row_str = " ".join(clean_row)
                                
                                if "Median household income" in row_str and "private households" in row_str:
                                    # Ensure we aren't reading the Calgary column
                                    # Usually Community is Col 1, Calgary is Col 2
                                    # But sometimes table is transposed? No, usually standard.
                                    # If table[0][0] is "Calgary", skip table.
                                    if table[0] and "Calgary" in str(table[0][0]):
                                        break 
                                        
                                    for cell in clean_row:
                                        match = re.search(r'\$([\d,]+)', cell)
                                        if match:
                                            val = int(match.group(1).replace(',', ''))
                                            if val > 0:
                                                data['median_income'] = val
                                                break
                                    if data['median_income']: break
                            if data['median_income']: break

                        # --- Indigenous Identity ---
                        elif "Indigenous identity" in str(table):
                            if table[0] and "Calgary" in str(table[0][0]): continue
                            
                            for row in table:
                                clean_row = [str(x).replace('\n', ' ').strip() for x in row if x]
                                if not clean_row: continue
                                
                                if clean_row[0] == "Indigenous identity" and len(clean_row) >= 3:
                                    try:
                                        num = int(clean_row[1].replace(',', ''))
                                        pct = clean_row[2]
                                        data['indigenous_identity'] = {"number": num, "percentage": pct}
                                    except ValueError:
                                        pass

                        # --- Immigration ---
                        elif "Non-immigrants" in str(table) or "Immigrants" in str(table):
                            if table[0] and "Calgary" in str(table[0][0]): continue
                            
                            immigration_data = {}
                            found_any = False
                            for row in table:
                                clean_row = [str(x).replace('\n', ' ').strip() for x in row if x]
                                if not clean_row: continue
                                
                                label = clean_row[0]
                                if label in ["Non-immigrants", "Immigrants", "Non-permanent residents"]:
                                    if len(clean_row) >= 3:
                                        try:
                                            num = int(clean_row[1].replace(',', ''))
                                            pct = clean_row[2]
                                            immigration_data[label] = {"number": num, "percentage": pct}
                                            found_any = True
                                        except ValueError:
                                            pass
                            if found_any:
                                if data['immigrants']: data['immigrants'].update(immigration_data)
                                else: data['immigrants'] = immigration_data

            # 1. Population (Regex on full text)
            clean_text = full_text.replace('\n', ' ')
            pop_phrases = [
                "Population in private households to whom low- income concepts are applicable",
                "Population in private households to whom low-income concepts are applicable",
                "Population in private households"
            ]
            
            for phrase in pop_phrases:
                pop_idx = clean_text.find(phrase)
                if pop_idx != -1:
                    snippet = clean_text[pop_idx:pop_idx+200]
                    nums = re.findall(r'([\d,]{2,})', snippet)
                    for num in nums:
                        val = int(num.replace(',', ''))
                        if val > 100 and val not in [2021, 2019, 2016]: 
                            data['population'] = val
                            break
                    if data['population']: break
            
            # 3. Low Income %
            lim_idx = full_text.find("Prevalence of low income based on the Low-income measure")
            if lim_idx != -1:
                snippet = full_text[lim_idx:lim_idx+300]
                pct_match = re.search(r'(\d+\.?\d*)%', snippet)
                if pct_match:
                    data['low_income_pct'] = float(pct_match.group(1))

        return data

    except Exception as e:
        print(f"Error scraping {name}: {e}")
        return None

def main():
    print("Starting full scrape...")
    links = get_community_links()
    
    # Limit for testing
    # links = {k: v for k, v in links.items() if k == "South Calgary"}
    # links = dict(list(links.items())[:5])
    
    # If South Calgary was missed before, let's make sure we get it now.
    # We can just run for all, or filter for missing ones if we want to be fast.
    # For now, let's run for all to be safe, or just South Calgary to test.
    # links = {k: v for k, v in links.items() if k == "South Calgary"}
    
    results = {}
    
    print(f"Starting thread pool with {len(links)} links...")
    # Use ThreadPoolExecutor
    # Increased workers to 10 for faster processing
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_name = {executor.submit(scrape_community, name, url): name for name, url in links.items()}
        
        count = 0
        total = len(links)
        
        for future in concurrent.futures.as_completed(future_to_name):
            name = future_to_name[future]
            count += 1
            try:
                data = future.result()
                if data:
                    print(f"[{count}/{total}] Scraped {name}: Pop={data.get('population')}, Inc={data.get('median_income')}")
                    results[name] = data
                else:
                    print(f"[{count}/{total}] Failed/No Data for {name}")
            except Exception as e:
                print(f"[{count}/{total}] Exception for {name}: {e}")
                
    # Save to JSON
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results, f, indent=4)
        
    print(f"Saved data for {len(results)} communities to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
