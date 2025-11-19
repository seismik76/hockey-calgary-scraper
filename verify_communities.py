from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Community, Team

DB_NAME = "hockey_calgary.db"
engine = create_engine(f"sqlite:///{DB_NAME}")
Session = sessionmaker(bind=engine)
session = Session()

communities = session.query(Community).all()
print("Remaining Communities and Team Counts:")
for c in communities:
    team_count = session.query(Team).filter_by(community_id=c.id).count()
    print(f"- {c.name}: {team_count} teams")

total_teams = session.query(Team).count()
print(f"Total Teams: {total_teams}")

session.close()
