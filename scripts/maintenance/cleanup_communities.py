import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Community, Team, Standing, Base
from utilities.utils import ALLOWED_COMMUNITIES

# Database setup
DB_NAME = "hockey_calgary.db"
engine = create_engine(f"sqlite:///{DB_NAME}")
Session = sessionmaker(bind=engine)
session = Session()

def cleanup_database():
    print("Starting database cleanup...")
    print(f"Allowed Communities: {ALLOWED_COMMUNITIES}")

    # 1. Find communities to delete
    all_communities = session.query(Community).all()
    communities_to_delete = []
    
    for community in all_communities:
        if community.name not in ALLOWED_COMMUNITIES:
            communities_to_delete.append(community)
    
    print(f"Found {len(communities_to_delete)} communities to delete.")
    
    for community in communities_to_delete:
        print(f"Deleting community: {community.name}")
        
        # 2. Find teams associated with this community
        teams = session.query(Team).filter(Team.community_id == community.id).all()
        print(f"  - Found {len(teams)} teams to delete.")
        
        for team in teams:
            # 3. Delete standings associated with this team
            standings = session.query(Standing).filter(Standing.team_id == team.id).all()
            print(f"    - Deleting {len(standings)} standings records.")
            for standing in standings:
                session.delete(standing)
            
            # Delete the team
            session.delete(team)
        
        # Delete the community
        session.delete(community)
        
    # Commit changes
    try:
        session.commit()
        print("Cleanup complete. Database updated.")
    except Exception as e:
        session.rollback()
        print(f"Error during cleanup: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    cleanup_database()
