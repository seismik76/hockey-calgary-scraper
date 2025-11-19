from sqlalchemy.orm import Session
from database import SessionLocal
from models import Team, Community

def check_communities():
    db = SessionLocal()
    communities = db.query(Community).order_by(Community.name).all()
    
    print(f"Found {len(communities)} communities.")
    for c in communities:
        team_count = db.query(Team).filter_by(community_id=c.id).count()
        example_team = db.query(Team).filter_by(community_id=c.id).first()
        team_name = example_team.name if example_team else "None"
        print(f"'{c.name}' ({team_count} teams) - Ex: {team_name}")
        
    db.close()

if __name__ == "__main__":
    check_communities()
