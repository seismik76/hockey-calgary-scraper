import re
import json
import os

MAP_FILE = "community_map.json"

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
    
    # Heuristic: Remove trailing numbers and colors
    # e.g. "Bow Valley 1" -> "Bow Valley"
    # "Trails West 5 Red" -> "Trails West"
    
    # Remove trailing numbers
    base_name = re.sub(r'\s+\d+$', '', team_name)
    
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
    
    return base_name.strip()
