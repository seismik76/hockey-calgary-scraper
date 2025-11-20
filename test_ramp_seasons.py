from scraper import get_ramp_leagues, get_soup, fetch_ramp_data, save_standings, load_community_map
from database import init_db, SessionLocal
from models import Season, League

def test_ramp_seasons_loop():
    init_db()
    db = SessionLocal()
    community_map = load_community_map()
    
    print("Fetching RAMP leagues...")
    ramp_leagues = get_ramp_leagues()
    
    # Filter for U11 Tier 1 or similar to test
    target = next((l for l in ramp_leagues if "Tier 1" in l['name']), None)
    if not target:
        target = ramp_leagues[0]
        
    print(f"Testing with {target['name']} ({target['url']})...")
    
    # Copied logic from scraper.py (updated version)
    soup = get_soup(target['url'])
    if not soup: return

    # 1. Find Seasons
    ramp_seasons = []
    season_select = soup.find('select', id='ddlSeason')
    if season_select:
        for opt in season_select.find_all('option'):
            val = opt.get('value')
            text = opt.get_text(strip=True)
            if val and val != '0':
                ramp_seasons.append({'name': text, 'id': val})
    
    if not ramp_seasons:
        ramp_seasons.append({'name': "2025-2026", 'id': None})
        
    print(f"Found Seasons: {ramp_seasons}")

    # 2. Find Game Types
    game_types = []
    gt_select = soup.find('select', id='ddlGameType')
    if gt_select:
        for opt in gt_select.find_all('option'):
            val = opt.get('value')
            text = opt.get_text(strip=True)
            if val and val != '0': # Skip "All Game Types"
                game_types.append({'name': text, 'id': val})
    
    if not game_types:
        game_types.append({'name': 'Regular', 'id': 0})
        
    print(f"Found Game Types: {game_types}")

    # Iterate Seasons
    for r_season in ramp_seasons:
        season_name = r_season['name']
        season_id = r_season['id']
        
        # Ensure season exists in DB
        season = db.query(Season).filter_by(name=season_name).first()
        if not season:
            season = Season(name=season_name)
            db.add(season)
            db.commit()
            db.refresh(season)
        
        # Iterate Game Types
        for gt in game_types:
            print(f"  Fetching RAMP {season_name} - {gt['name']} (SID: {season_id}, GTID: {gt['id']})...")
            
            # Determine League (Create specific if needed)
            if gt['id'] == 0:
                target_league = None # Should fetch original league object but for test we skip
            else:
                specific_league_name = f"{target['name']} - {gt['name']}"
                specific_league_slug = f"{target['slug']}-{gt['name'].lower()}"
                specific_league_type = 'Seeding' if 'Seeding' in gt['name'] else 'Regular'
                
                target_league = db.query(League).filter_by(
                    slug=specific_league_slug,
                    stream='RAMP',
                    type=specific_league_type
                ).first()
                
                if not target_league:
                    target_league = League(
                        name=specific_league_name,
                        slug=specific_league_slug,
                        stream='RAMP',
                        type=specific_league_type
                    )
                    db.add(target_league)
                    db.commit()
                    db.refresh(target_league)
            
            if target_league:
                data = fetch_ramp_data(target['url'], gt['id'], season_id)
                print(f"    Got {len(data)} records.")
                save_standings(db, data, season, target_league, community_map)

if __name__ == "__main__":
    test_ramp_seasons_loop()
