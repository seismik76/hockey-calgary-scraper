import re
import json
import os

from utilities.tiering_logic import parse_tier_info

MAP_FILE = "community_map.json"

# Tokens recognised as "team colour" suffixes. Lower-case lookup.
_TEAM_COLOR_TOKENS = {
    'red', 'blue', 'white', 'black', 'gold', 'silver', 'green', 'yellow',
    'grey', 'gray', 'orange', 'teal', 'navy', 'maroon', 'purple', 'pink',
    'lime', 'cyan', 'magenta', 'brown', 'beige', 'royal', 'sky',
}

# Words to preserve in upper case when normalising an all-caps team name.
# Anything else gets Title-cased. Age tokens like "U11"/"U13" are handled
# separately via the "contains-a-digit" check.
_HOCKEY_ACRONYMS = {'AA', 'AAA', 'HADP', 'NBC', 'BC'}


def normalize_team_name(name):
    """
    Canonicalise team-name casing.

    Upstream RAMP / Alberta One scrapes report team names entirely in upper
    case (`KNIGHTS U11 AA`), while the City Championships / Esso tournament
    feeds report them in mixed case (`Knights U11 AA`). Stored as-is, the
    two variants become separate Team rows with split standings.

    Strategy: leave already-mixed-case names alone; for fully-upper inputs,
    Title-case each word except recognised hockey acronyms (`AA`, `HADP`,
    etc.) and tokens containing digits (`U11`, `U13`).
    """
    if not name:
        return name
    name = name.strip()
    # Already mixed-case → trust the upstream and leave it alone.
    if any(c.islower() for c in name):
        return name
    return ' '.join(
        word
        if (any(c.isdigit() for c in word) or word.upper() in _HOCKEY_ACRONYMS)
        else word.title()
        for word in name.split()
    )


def parse_team_differentiator(team_name):
    """
    Extract (number, color) from the trailing tokens of a team name.

    Upstream sources format team names inconsistently — the constants we can
    reliably recover are the team's number (1, 2, ...) and color suffix (Red,
    Gold, ...). Everything else (community, age, tier) lives on the league row
    already, so we don't need to parse it from the team name.

    Examples:
      "Southwest 2 Gold"               -> (2, "Gold")
      "U11 BOW RIVER BRUINS 4 BLACK"   -> (4, "Black")
      "Southwest U11 AA"               -> (None, None)
      "Bow River HADP"                 -> (None, None)
    """
    tokens = (team_name or '').split()
    color = None
    if tokens and tokens[-1].lower() in _TEAM_COLOR_TOKENS:
        color = tokens[-1].title()
        tokens = tokens[:-1]
    number = None
    if tokens and tokens[-1].isdigit():
        number = int(tokens[-1])
    return number, color


def extract_tier_label(league_name):
    """
    Return a short, comparable tier label: 'AA', 'HADP', '1', '2', ..., or 'Other'.

    parse_tier_info collapses AA and HADP into a single 'AA' bucket; we
    disambiguate here from the raw league name so users can filter on HADP
    separately from AA.
    """
    info = parse_tier_info(league_name or '')
    tier = info.get('tier')
    upper = (league_name or '').upper()
    if tier == 'AA':
        return 'HADP' if 'HADP' in upper else 'AA'
    if isinstance(tier, int):
        return str(tier)
    return 'Other'


def standardize_team_label(team_name, league_name, community):
    """
    Compose a clean, consistent team display name from the league + community
    (the canonical source for age/tier/community) plus the parsed number/color
    from the team name itself.

      "Southwest 2 Gold" in "U11 Tier 2 South"        -> "Southwest U11 Tier 2 #2 Gold"
      "BOW RIVER BRUINS U11 AA" in "U11 AA"           -> "Bow River U11 AA"
      "U18 Tier 2 NBC" team "Knights 2"               -> "Knights U18 Tier 2 NBC #2"
    """
    age_match = re.search(r'U\d{1,2}', league_name or '', re.IGNORECASE)
    age = age_match.group().upper() if age_match else ''

    info = parse_tier_info(league_name or '')
    tier_label = extract_tier_label(league_name)
    if tier_label in ('AA', 'HADP'):
        tier_str = tier_label
    elif tier_label.isdigit():
        tier_str = f"Tier {tier_label}"
        if info.get('stream') == 'NBC':
            tier_str += ' NBC'
    else:
        tier_str = ''

    number, color = parse_team_differentiator(team_name)

    parts = [community or '', age, tier_str]
    if number is not None:
        parts.append(f"#{number}")
    if color:
        parts.append(color)
    return ' '.join(p for p in parts if p)

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
    
    # Known Community Mappings — ORDER MATTERS for overlapping names.
    # Iteration is insertion order: the FIRST substring match wins, so put
    # specific identifiers (association codes + full community names) BEFORE
    # generic nicknames (e.g. "NWCAA Bruins" should match NWCAA, not BRUINS).
    known_map = {
        # 1. Association codes (most specific)
        "GHC": "Girls Hockey Calgary",
        "GIRLS HOCKEY CALGARY": "Girls Hockey Calgary",
        "CBHA": "CBHA",
        "NWCAA": "North West",
        "CNHA": "Calgary Northstars",
        "CRAA": "Calgary Royals",

        # 2. Full community names
        "GLENLAKE": "Glenlake",
        "BOW VALLEY": "Bow Valley",
        "BOW RIVER": "Bow River",
        "SPRINGBANK": "Springbank",
        "CROWFOOT": "Crowfoot",
        "TRAILS WEST": "Trails West",
        "SIMONS VALLEY": "Simons Valley",
        "SOUTH WEST": "Southwest",
        "SOUTHWEST": "Southwest",
        "BLACKFOOT": "Blackfoot",
        "MCKNIGHT": "McKnight",
        "MIDNAPORE": "Midnapore",
        "LAKE BONAVISTA": "Lake Bonavista",
        "NORTH WEST": "North West",
        "NORTHWEST": "North West",
        "CALGARY NORTHSTARS": "Calgary Northstars",
        "CALGARY ROYALS": "Calgary Royals",
        "KNIGHTS": "Knights",
        "WOLVERINES": "Wolverines",
        "RAIDERS": "Raiders",

        # 3. Generic team nicknames (ambiguous — only used when nothing above matched)
        "BRUINS": "Bow River",
        "MUSTANGS": "McKnight",
        "MAVERICKS": "Midnapore",
        "WARRIORS": "North West",
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
