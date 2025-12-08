import json
import os

DEMOGRAPHICS_FILE = 'data/reference/neighborhood_demographics.json'
INCOME_FILE = 'data/reference/neighborhood_incomes.json'

def patch_demographics():
    if not os.path.exists(DEMOGRAPHICS_FILE):
        print(f"Error: {DEMOGRAPHICS_FILE} not found.")
        return

    with open(DEMOGRAPHICS_FILE, 'r') as f:
        data = json.load(f)

    # --- 1. Manual Patches (Existing) ---
    # Tsuut'ina Nation
    if "Tsuut'ina Nation" in data:
        print("Patching Tsuut'ina Nation...")
        data["Tsuut'ina Nation"]["population"] = 2269
        data["Tsuut'ina Nation"]["median_income"] = 31500
        data["Tsuut'ina Nation"]["indigenous_identity"] = {"number": 2246, "percentage": "99.0%"}
        data["Tsuut'ina Nation"]["source"] = "CIRNAC 2021 (Pop) / AB First Nations Median Proxy (Income)"

    # South Calgary (if missing or incomplete)
    if "South Calgary" in data:
        # Ensure it has the manual data if the scraper missed it
        if not data["South Calgary"].get("median_income"):
             print("Patching South Calgary...")
             data["South Calgary"].update({
                "population": 4535,
                "median_income": 87000,
                "indigenous_identity": {"number": 165, "percentage": "4.0%"},
                "immigrants": {
                    "Non-immigrants": {"number": 3600, "percentage": "79.0%"},
                    "Immigrants": {"number": 855, "percentage": "19.0%"},
                    "Non-permanent residents": {"number": 85, "percentage": "2.0%"}
                },
                "source": "2021 Census Profile (Manual Extraction)"
             })

    # --- 2. Proxy Mappings (New) ---
    proxies = {
        "Hanson Ranch": "Hidden Valley",
        "Wentworth": "West Springs",
        "Elgin": "McKenzie Towne",
        "Silverton": "Silverado",
        "Creekstone": "Pine Creek",
        "Providence": "Evergreen", # Closest established
        "Point McKay": "Point Mckay" # Alias fix if 'Point Mckay' exists
    }

    for child, parent in proxies.items():
        if child not in data:
            # Check if parent exists
            parent_data = data.get(parent)
            
            # Handle Point McKay case sensitivity
            if not parent_data and parent == "Point Mckay":
                 # Try finding it case-insensitive
                 for k in data.keys():
                     if k.lower() == "point mckay":
                         parent_data = data[k]
                         break
            
            if parent_data:
                print(f"Creating {child} using proxy {parent}...")
                # Deep copy to avoid reference issues
                child_data = json.loads(json.dumps(parent_data))
                
                # Update Source to reflect proxy
                child_data["name"] = child
                child_data["source"] = f"Proxy: {parent} (2021 Census)"
                
                # For sub-communities (Hanson, Wentworth, Elgin), population is likely included in parent.
                # We should probably NOT double count population if we can avoid it, 
                # OR we accept it for the sake of the weighted average (which needs a weight).
                # Decision: Keep population for weighting, but mark source clearly.
                
                data[child] = child_data
            else:
                print(f"Warning: Proxy parent {parent} not found for {child}")

    # --- 3. Industrial / Zero Pop ---
    zeros = ["Royal Vista", "Stonegate Landing", "Keystone", "Zone 9"]
    for z in zeros:
        if z not in data:
            print(f"Setting zero population for {z}...")
            data[z] = {
                "name": z,
                "population": 0,
                "median_income": 0,
                "source": "Industrial/Non-Residential"
            }

    # Save Demographics
    with open(DEMOGRAPHICS_FILE, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"Updated {DEMOGRAPHICS_FILE}")

    # --- Sync to Incomes File ---
    if os.path.exists(INCOME_FILE):
        with open(INCOME_FILE, 'r') as f:
            incomes = json.load(f)
        
        # Update incomes from the patched demographics
        for name, info in data.items():
            if info.get("median_income"):
                incomes[name] = {
                    "income": info["median_income"],
                    "source": info.get("source", "2021 Census")
                }
        
        with open(INCOME_FILE, 'w') as f:
            json.dump(incomes, f, indent=4)
        print(f"Synced to {INCOME_FILE}")

if __name__ == "__main__":
    patch_demographics()
