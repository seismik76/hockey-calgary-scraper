from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from models import League, Season, Standing

DB_NAME = "hockey_calgary.db"
engine = create_engine(f"sqlite:///{DB_NAME}")
Session = sessionmaker(bind=engine)
session = Session()

print("--- U11 Data Summary ---")

# Find all leagues with "U11" in the name
u11_leagues = session.query(League).filter(League.name.like("%U11%")).all()
print(f"Found {len(u11_leagues)} U11 leagues.")

for league in u11_leagues:
    # Count standings per season for this league
    standings_by_season = session.query(Season.name, func.count(Standing.id))\
        .join(Standing, Standing.season_id == Season.id)\
        .filter(Standing.league_id == league.id)\
        .group_by(Season.name).all()
    
    if standings_by_season:
        print(f"\nLeague: {league.name} (ID: {league.id}, Stream: {league.stream})")
        for season_name, count in standings_by_season:
            print(f"  - {season_name}: {count} records")

session.close()
