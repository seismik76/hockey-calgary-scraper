import json
import os

def check_missing():
    # Load Target Neighborhoods (from Associations)
    with open('data/reference/association_neighborhoods.json', 'r') as f:
        assoc_map = json.load(f)
    
    all_targets = set()
    for assoc, hoods in assoc_map.items():
        for hood in hoods:
            all_targets.add(hood)
            
    # Load Scraped Data
    if os.path.exists('data/reference/neighborhood_demographics.json'):
        with open('data/reference/neighborhood_demographics.json', 'r') as f:
            demo_data = json.load(f)
    else:
        demo_data = {}
        
    # Load Legacy Data (for reference)
    if os.path.exists('data/reference/neighborhood_incomes.json'):
        with open('data/reference/neighborhood_incomes.json', 'r') as f:
            legacy_data = json.load(f)
    else:
        legacy_data = {}

    missing_entries = []
    incomplete_entries = []
    
    print(f"Total Target Neighborhoods: {len(all_targets)}")
    print(f"Total Scraped Neighborhoods: {len(demo_data)}")
    
    for hood in all_targets:
        if hood not in demo_data:
            # Check if we have legacy data
            legacy_val = legacy_data.get(hood)
            missing_entries.append({
                "name": hood,
                "legacy_data": legacy_val
            })
        else:
            # Check for nulls
            data = demo_data[hood]
            if data.get('median_income') is None or data.get('population') is None:
                incomplete_entries.append({
                    "name": hood,
                    "missing_fields": [k for k in ['median_income', 'population'] if data.get(k) is None],
                    "legacy_data": legacy_data.get(hood)
                })

    print("\n--- Missing Entries (Not in Scraper Output) ---")
    for item in missing_entries:
        print(f"{item['name']} (Legacy: {item['legacy_data']})")
        
    print("\n--- Incomplete Entries (Null Values) ---")
    for item in incomplete_entries:
        print(f"{item['name']} - Missing: {item['missing_fields']} (Legacy: {item['legacy_data']})")

if __name__ == "__main__":
    check_missing()
