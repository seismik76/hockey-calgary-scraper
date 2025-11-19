from sqlalchemy.orm import Session
from database import SessionLocal
from models import Team, Community
from utils import normalize_community_name, load_community_map

def fix_communities():
    db = SessionLocal()
    teams = db.query(Team).all()
    community_map = load_community_map()
    
    print(f"Checking {len(teams)} teams for community updates...")
    
    updated_count = 0
    for team in teams:
        old_comm_id = team.community_id
        
        # Re-calculate community name
        new_comm_name = normalize_community_name(team.name, community_map)
        
        # Get or create new community
        community = db.query(Community).filter_by(name=new_comm_name).first()
        if not community:
            community = Community(name=new_comm_name)
            db.add(community)
            db.commit()
            db.refresh(community)
            print(f"Created new community: {new_comm_name}")
            
        if team.community_id != community.id:
            team.community_id = community.id
            updated_count += 1
            # print(f"Updated {team.name} -> {new_comm_name}")
            
    db.commit()
    
    # Cleanup empty communities
    print("Cleaning up empty communities...")
    empty_communities = []
    all_communities = db.query(Community).all()
    for c in all_communities:
        if not c.teams:
            empty_communities.append(c)
            
    for c in empty_communities:
        db.delete(c)
        
    db.commit()
    print(f"Removed {len(empty_communities)} empty communities.")
    
    db.close()
    print(f"Fixed {updated_count} team mappings.")

if __name__ == "__main__":
    fix_communities()
