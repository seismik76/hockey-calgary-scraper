from sqlalchemy.orm import Session
from database import SessionLocal
from models import Season, Standing
from collections import defaultdict

def fix_seasons():
    db = SessionLocal()
    seasons = db.query(Season).all()
    
    print(f"Found {len(seasons)} seasons.")
    
    # Group by normalized name
    grouped = defaultdict(list)
    for s in seasons:
        norm_name = s.name.replace('/', '-')
        grouped[norm_name].append(s)
        
    for norm_name, season_list in grouped.items():
        print(f"Processing '{norm_name}' (Count: {len(season_list)})...")
        
        target_season = None
        
        # 1. Find a target season (prefer one that is already normalized)
        for s in season_list:
            if s.name == norm_name:
                target_season = s
                break
        
        # If no exact match, pick the first one and rename it later
        if not target_season:
            target_season = season_list[0]
            if target_season.name != norm_name:
                print(f"  Renaming '{target_season.name}' to '{norm_name}'...")
                target_season.name = norm_name
                db.commit()
                
        # 2. Merge others into target
        for s in season_list:
            if s.id == target_season.id:
                continue
                
            print(f"  Merging '{s.name}' (ID: {s.id}) into '{target_season.name}' (ID: {target_season.id})...")
            
            # Move standings
            standings = db.query(Standing).filter_by(season_id=s.id).all()
            for st in standings:
                # Check if standing already exists in target season
                existing = db.query(Standing).filter_by(
                    season_id=target_season.id,
                    league_id=st.league_id,
                    team_id=st.team_id
                ).first()
                
                if existing:
                    db.delete(st)
                else:
                    st.season_id = target_season.id
            
            db.commit()
            
            # Delete the old season
            db.delete(s)
            db.commit()
            
    db.close()
    print("Season fix complete.")

if __name__ == "__main__":
    fix_seasons()