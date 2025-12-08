import json
import os

DEMO_FILE = 'data/reference/neighborhood_demographics.json'
INCOME_FILE = 'data/reference/neighborhood_incomes.json'

def sync_incomes():
    with open("debug_sync.txt", "w") as f: f.write("Started\n")
    if not os.path.exists(DEMO_FILE):
        print("Demographics file not found.")
        return

    with open(DEMO_FILE, 'r') as f:
        demo_data = json.load(f)
        
    if os.path.exists(INCOME_FILE):
        with open(INCOME_FILE, 'r') as f:
            income_data = json.load(f)
    else:
        income_data = {}

    count = 0
    for name, data in demo_data.items():
        inc = data.get('median_income')
        if inc:
            # Update income file
            income_data[name] = {
                "income": inc,
                "source": "2021 Census (Scraped)"
            }
            count += 1
            
    with open(INCOME_FILE, 'w') as f:
        json.dump(income_data, f, indent=4)
        
    print(f"Updated {count} entries in {INCOME_FILE} from scraped data.")

if __name__ == "__main__":
    sync_incomes()
