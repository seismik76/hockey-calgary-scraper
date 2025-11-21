from scraper import sync_data, get_ramp_leagues, fetch_ramp_data, save_standings, load_community_map, get_soup
from database import init_db, SessionLocal
from models import Season, League

def test_ramp_seeding():
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
    
    # Copied logic from scraper.py
    current_season_name = "2025-2026" 
    season = db.query(Season).filter_by(name=current_season_name).first()
    if not season:
        season = Season(name=current_season_name)
        db.add(season)
        db.commit()
        db.refresh(season)
    
    soup = get_soup(target['url'])
    game_types = []
    if soup:
        select = soup.find('select', id='ddlGameType')
        if select:
            for opt in select.find_all('option'):
                val = opt.get('value')
                text = opt.get_text(strip=True)
                if val and val != '0': # Skip "All Game Types"
                    game_types.append({'name': text, 'id': val})
    
    print(f"Found Game Types: {game_types}")
    
    for gt in game_types:
        print(f"  Fetching RAMP {gt['name']} (ID: {gt['id']})...")
        
        specific_league_name = f"{target['name']} - {gt['name']}"
        specific_league_slug = f"{target['slug']}-{gt['name'].lower()}"
        specific_league_type = 'Seeding' if 'Seeding' in gt['name'] else 'Regular'
        
        specific_league = db.query(League).filter_by(
            slug=specific_league_slug,
            stream='RAMP',
            type=specific_league_type
        ).first()
        
        if not specific_league:
            specific_league = League(
                name=specific_league_name,
                slug=specific_league_slug,
                stream='RAMP',
                type=specific_league_type
            )
            db.add(specific_league)
            db.commit()
            db.refresh(specific_league)
            
        data = fetch_ramp_data(target['url'], gt['id'])
        print(f"    Got {len(data)} records.")
        save_standings(db, data, season, specific_league, community_map)

if __name__ == "__main__":
    test_ramp_seeding()
