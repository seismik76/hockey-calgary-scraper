import re
import json
import os

MAP_FILE = "community_map.json"

# Allowed Communities (User Specified)
ALLOWED_COMMUNITIES = {
    "Bow River",
    "North West",
    "Trails West",
    "Springbank",
    "Raiders",
    "McKnight",
    "Glenlake",
    "Bow Valley",
    "Wolverines",
    "Knights",
    "Southwest"
}

def load_community_map():
    if os.path.exists(MAP_FILE):
        with open(MAP_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_community_map(mapping):
    with open(MAP_FILE, 'w') as f:
        json.dump(mapping, f, indent=4)

def normalize_community_name(team_name, mapping=None):
    if mapping is None:
        mapping = load_community_map()
    
    # Check if exact match in mapping
    if team_name in mapping:
        return mapping[team_name]
        
    name_upper = team_name.upper()
    
    # Known Community Mappings (Order matters for overlapping names)
    # Based on user feedback and common Calgary associations
    known_map = {
        "GHC": "Girls Hockey Calgary",
        "GIRLS HOCKEY CALGARY": "Girls Hockey Calgary",
        "CBHA": "CBHA",
        "GLENLAKE": "Glenlake",
        "BOW VALLEY": "Bow Valley",
        "BOW RIVER": "Bow River",
        "BRUINS": "Bow River", 
        "SPRINGBANK": "Springbank",
        "CROWFOOT": "Crowfoot",
        "TRAILS WEST": "Trails West",
        "SIMONS VALLEY": "Simons Valley",
        "SOUTH WEST": "Southwest",
        "SOUTHWEST": "Southwest",
        "BLACKFOOT": "Blackfoot",
        "MCKNIGHT": "McKnight",
        "MUSTANGS": "McKnight",
        "MIDNAPORE": "Midnapore",
        "MAVERICKS": "Midnapore",
        "LAKE BONAVISTA": "Lake Bonavista",
        "NORTH WEST": "North West",
        "NORTHWEST": "North West",
        "NWCAA": "North West",
        "WARRIORS": "North West",
        "CALGARY NORTHSTARS": "Calgary Northstars",
        "CNHA": "Calgary Northstars",
        "CALGARY ROYALS": "Calgary Royals",
        "CRAA": "Calgary Royals",
        "KNIGHTS": "Knights",
        "WOLVERINES": "Wolverines",
        "RAIDERS": "Raiders"
    }
    
    normalized_name = None
    for key, value in known_map.items():
        if key in name_upper:
            normalized_name = value
            break
    
    if normalized_name:
        if normalized_name in ALLOWED_COMMUNITIES:
            return normalized_name
        else:
            return None # Filter out unwanted communities

    # Heuristic: Remove trailing numbers and colors
    # e.g. "Bow Valley 1" -> "Bow Valley"
    # "Trails West 5 Red" -> "Trails West"
    
    # Remove Age Category prefixes (e.g. "U13 ", "U11 ")
    base_name = re.sub(r'^U\d+\s+', '', team_name, flags=re.IGNORECASE)
    
    # Remove trailing numbers
    base_name = re.sub(r'\s+\d+$', '', base_name)
    
    # Remove trailing colors (common ones)
    colors = [
        'Red', 'Blue', 'White', 'Black', 'Gold', 'Silver', 'Green', 'Yellow', 
        'Grey', 'Gray', 'Orange', 'Teal', 'Navy', 'Maroon', 'Purple', 'Pink', 
        'Lime', 'Cyan', 'Magenta', 'Brown', 'Beige', 'Royal', 'Sky'
    ]
    for color in colors:
        # Case insensitive check for color at the end
        if re.search(r'\b' + re.escape(color) + r'$', base_name, re.IGNORECASE):
            base_name = re.sub(r'\s+\b' + re.escape(color) + r'$', '', base_name, flags=re.IGNORECASE)
            break
            
    # Remove trailing numbers again if color was removed
    base_name = re.sub(r'\s+\d+$', '', base_name)
    
    final_name = base_name.strip()
    if final_name in ALLOWED_COMMUNITIES:
        return final_name
        
    return None
