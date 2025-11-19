from sqlalchemy import create_engine, text
import pandas as pd

DB_URL = "sqlite:///hockey_calgary.db"
engine = create_engine(DB_URL)

def inspect_u11_tier1():
    with engine.connect() as conn:
        # Find the league ID for U11 Tier 1 North
        print("--- Searching for U11 Tier 1 Leagues ---")
        query = text("SELECT id, name, stream FROM leagues WHERE name LIKE '%U11%Tier%1%'")
        result = conn.execute(query)
        leagues = result.fetchall()
        
        for l in leagues:
            print(f"League: {l.name} (ID: {l.id})")
            
            # Get standings for this league
            print(f"  Standings for {l.name}:")
            s_query = text("""
                SELECT t.name as team_name, c.name as community_name, st.gp, st.pts
                FROM standings st
                JOIN teams t ON st.team_id = t.id
                JOIN communities c ON t.community_id = c.id
                WHERE st.league_id = :lid
            """)
            s_result = conn.execute(s_query, {"lid": l.id})
            standings = s_result.fetchall()
            for row in standings:
                print(f"    - {row.team_name} (Comm: {row.community_name}) - GP: {row.gp}, PTS: {row.pts}")

if __name__ == "__main__":
    inspect_u11_tier1()