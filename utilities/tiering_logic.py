import re

def parse_tier_info(league_name):
    """
    Parses league name to extract Tier and Stream (BC/NBC).
    Returns: {'tier': int|str, 'stream': 'BC'|'NBC'|None}
    """
    league_name = league_name.upper()
    
    # Determine Stream (mainly for U15/U18)
    stream = 'BC' # Default for U11/U13 or unspecified
    if 'NBC' in league_name or 'NON-BODY CHECKING' in league_name or 'NON BODY CHECKING' in league_name:
        stream = 'NBC'
        
    # Check for AA / HADP
    if 'AA' in league_name or 'HADP' in league_name:
        return {'tier': 'AA', 'stream': stream}
        
    # Extract Tier Number
    tier = None
    
    # Try finding "Tier X"
    match = re.search(r'TIER\s+(\d+)', league_name)
    if match:
        tier = int(match.group(1))
    else:
        # Try finding "NBC X"
        match = re.search(r'NBC\s+(\d+)', league_name)
        if match:
            tier = int(match.group(1))
        else:
            # Fallback: Look for digits?
            pass
            
    return {'tier': tier, 'stream': stream}

def get_u11_u13_distribution(total_teams):
    """
    Returns the expected distribution of teams across Tiers 1-6
    based on the Alberta One Standardized Tiering Grids (approximate).
    
    Logic inferred:
    - Base = total // 6
    - Remainder distributed to Tiers in priority: 3, 4, 5, 6, 2, 1
    """
    if total_teams == 0:
        return {}
        
    tiers = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
    
    # Special cases for small numbers based on text/common sense
    if total_teams == 1:
        return {1: 0, 2: 0, 3: 0, 4: 1, 5: 0, 6: 0} # Place in middle/lower
    if total_teams == 2:
        return {1: 0, 2: 1, 3: 1, 4: 0, 5: 0, 6: 0} # Split top/mid? Or Mid?
    if total_teams == 3:
        return {1: 0, 2: 1, 3: 1, 4: 1, 5: 0, 6: 0}
        
    # General Algorithm
    base = total_teams // 6
    remainder = total_teams % 6
    
    for t in tiers:
        tiers[t] = base
        
    # Priority for extras: 3, 4, 5, 6, 2, 1
    priority = [3, 4, 5, 6, 2, 1]
    
    for i in range(remainder):
        tiers[priority[i]] += 1
        
    return tiers

def get_u15_u18_split(total_teams):
    """
    Returns expected (BC_Count, NBC_Count).
    Based on approximate grid logic.
    """
    if total_teams == 0: return 0, 0
    if total_teams == 1: return 0, 1
    if total_teams == 2: return 1, 1
    if total_teams == 3: return 1, 2
    if total_teams == 4: return 2, 2
    if total_teams == 5: return 2, 3
    if total_teams == 6: return 3, 3
    if total_teams == 7: return 3, 4
    if total_teams == 8: return 4, 4
    if total_teams == 9: return 4, 5
    if total_teams == 10: return 5, 5
    
    # General rule: ~50/50, NBC slightly favored for odd numbers?
    bc = total_teams // 2
    nbc = total_teams - bc
    return bc, nbc

def get_u15_u18_tier_distribution(stream_teams):
    """
    Returns distribution across Tier 1, 2, 3 for a given stream (BC or NBC).
    Logic: 3 Tiers. Priority for extras: 3, 2, 1 (Bottom heavy).
    """
    if stream_teams == 0:
        return {1: 0, 2: 0, 3: 0}
        
    tiers = {1: 0, 2: 0, 3: 0}
    
    base = stream_teams // 3
    remainder = stream_teams % 3
    
    for t in tiers:
        tiers[t] = base
        
    # Priority: 3, 2, 1
    priority = [3, 2, 1]
    
    for i in range(remainder):
        tiers[priority[i]] += 1
        
    return tiers

def calculate_compliance(community_teams, age_group):
    """
    community_teams: List of dicts [{'tier': '1', 'count': 1}, ...]
    age_group: 'U11', 'U13', 'U15', 'U18'
    
    Returns:
    {
        'actual': {tier: count},
        'expected': {tier: count},
        'compliance_score': float (0-100),
        'notes': []
    }
    """
    total_teams = sum(t['count'] for t in community_teams)
    actual_dist = {t['tier']: t['count'] for t in community_teams}
    
    expected_dist = {}
    notes = []
    
    if age_group in ['U11', 'U13']:
        expected_dist = get_u11_u13_distribution(total_teams)
        # Normalize keys to match actual (strings vs ints)
        expected_dist = {str(k): v for k, v in expected_dist.items()}
        
    elif age_group in ['U15', 'U18']:
        # This is harder because we need to know which tiers are BC vs NBC in the input
        # We assume input keys are like "BC 1", "NBC 2", etc.
        # Or we map them before calling this.
        pass
        
    return expected_dist
