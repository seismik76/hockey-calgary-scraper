
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from utilities.tiering_logic import parse_tier_info, get_u11_u13_distribution

def verify_logic():
    test_leagues = [
        "U11 AA",
        "U11 HADP",
        "U11 Tier 1",
        "U13 AA",
        "U13 Tier 1 North",
        "U13 Tier 6"
    ]
    
    print("--- Parsing Test ---")
    teams_info = []
    for l in test_leagues:
        parsed = parse_tier_info(l)
        print(f"'{l}' -> {parsed}")
        if parsed['tier'] is not None:
            teams_info.append({'tier': parsed['tier']})
            
    # Simulation
    aa_teams = [t for t in teams_info if t['tier'] == 'AA']
    tiered_teams = [t for t in teams_info if isinstance(t['tier'], int)]
    
    print(f"\nTotal Teams Parsed: {len(teams_info)}")
    print(f"AA/HADP Count: {len(aa_teams)}")
    print(f"Tiered Count (Grid Input): {len(tiered_teams)}")
    
    grid = get_u11_u13_distribution(len(tiered_teams))
    print(f"Grid Distribution for {len(tiered_teams)} teams: {grid}")

if __name__ == "__main__":
    verify_logic()
