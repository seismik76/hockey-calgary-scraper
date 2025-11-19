import pandas as pd
from sqlalchemy import create_engine
from models import Standing, Team, League, Season, Community

DB_URL = "sqlite:///hockey_calgary.db"

def export_to_csv():
    engine = create_engine(DB_URL)
    
    query = """
    SELECT 
        s.name as Season,
        l.name as League,
        c.name as Community,
        t.name as Team,
        st.gp as GP,
        st.w as W,
        st.l as L,
        st.t as T,
        st.pts as PTS,
        st.gf as GF,
        st.ga as GA,
        st.diff as Diff
    FROM standings st
    JOIN seasons s ON st.season_id = s.id
    JOIN leagues l ON st.league_id = l.id
    JOIN teams t ON st.team_id = t.id
    JOIN communities c ON t.community_id = c.id
    ORDER BY s.name DESC, l.name, st.pts DESC
    """
    
    df = pd.read_sql(query, engine)
    df.to_csv("hockey_calgary_stats.csv", index=False)
    print("Data exported to hockey_calgary_stats.csv")

if __name__ == "__main__":
    export_to_csv()
