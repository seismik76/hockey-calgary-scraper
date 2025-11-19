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
    colors = ['Red', 'Blue', 'White', 'Black', 'Gold', 'Silver', 'Green', 'Yellow']
    for color in colors:
        if base_name.endswith(' ' + color):
            base_name = base_name[:-len(color)-1]
            break
            
    # Remove trailing numbers again if color was removed
    base_name = re.sub(r'\s+\d+$', '', base_name)
    
    return base_name.strip()
