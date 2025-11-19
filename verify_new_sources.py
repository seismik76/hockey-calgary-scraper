from scraper import get_ramp_leagues, get_teamlinkt_leagues, fetch_ramp_data, fetch_teamlinkt_data

def verify():
    print("--- Testing RAMP (U11) ---")
    ramp_leagues = get_ramp_leagues()
    if ramp_leagues:
        l = ramp_leagues[0]
        print(f"Testing league: {l['name']} ({l['url']})")
        
        data = fetch_ramp_data(l['url'])
        print(f"Found {len(data)} teams.")
        if data:
            print(f"Sample: {data[0]}")
    else:
        print("No RAMP leagues found.")

    print("\n--- Testing TeamLinkt (U13+) ---")
    tl_leagues = get_teamlinkt_leagues()
    if tl_leagues:
        l = tl_leagues[0]
        print(f"Testing league: {l['name']} ({l['url']})")
        
        data = fetch_teamlinkt_data(l['url'], l['slug'])
        print(f"Found {len(data)} teams.")
        if data:
            print(f"Sample: {data[0]}")
    else:
        print("No TeamLinkt leagues found.")

if __name__ == "__main__":
    verify()