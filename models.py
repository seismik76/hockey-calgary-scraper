from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Season(Base):
    __tablename__ = 'seasons'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False) # e.g., "2023-2024"

class League(Base):
    __tablename__ = 'leagues'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False) # e.g., "U11 Tier 1"
    slug = Column(String, nullable=False) # e.g., "u11-tier-1"
    stream = Column(String, nullable=False) # e.g., "community-council"
    __table_args__ = (UniqueConstraint('slug', 'stream', name='_league_slug_stream_uc'),)

class Community(Base):
    __tablename__ = 'communities'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False) # The master name
    # We can add aliases table if needed, or just handle mapping in code/json

class Team(Base):
    __tablename__ = 'teams'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False) # e.g., "Bow Valley 1"
    community_id = Column(Integer, ForeignKey('communities.id'))
    community = relationship("Community", back_populates="teams")
    
    # Unique constraint on name might be tricky if teams change names, but usually team name is unique per season/league context.
    # However, "Bow Valley 1" might exist in U11 and U13. So we treat them as the same "Team" entity? 
    # Or is "Team" just a name string?
    # Let's treat Team as a unique name for now.
    __table_args__ = (UniqueConstraint('name', name='_team_name_uc'),)

Community.teams = relationship("Team", order_by=Team.id, back_populates="community")

class Standing(Base):
    __tablename__ = 'standings'
    id = Column(Integer, primary_key=True)
    season_id = Column(Integer, ForeignKey('seasons.id'), nullable=False)
    league_id = Column(Integer, ForeignKey('leagues.id'), nullable=False)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False)
    
    gp = Column(Integer)
    w = Column(Integer)
    l = Column(Integer)
    t = Column(Integer)
    pts = Column(Integer)
    gf = Column(Integer)
    ga = Column(Integer)
    diff = Column(Integer)
    
    season = relationship("Season")
    league = relationship("League")
    team = relationship("Team")

    __table_args__ = (UniqueConstraint('season_id', 'league_id', 'team_id', name='_standing_uc'),)
