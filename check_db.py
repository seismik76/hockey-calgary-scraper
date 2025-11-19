from sqlalchemy import create_engine, text
import pandas as pd

DB_URL = "sqlite:///hockey_calgary.db"
engine = create_engine(DB_URL)

def check_data():
    with engine.connect() as conn:
        # Check Leagues
        print("--- Leagues in DB ---")
        result = conn.execute(text("SELECT name, type FROM leagues"))
        leagues = result.fetchall()
        for l in leagues:
            print(l)
            
        # Check Standings count by League
        print("\n--- Standings Count by League ---")
        query = """
        SELECT l.name, COUNT(st.id) as count
        FROM standings st
        JOIN leagues l ON st.league_id = l.id
        GROUP BY l.name
        """
        result = conn.execute(text(query))
        counts = result.fetchall()
        for c in counts:
            print(c)

if __name__ == "__main__":
    check_data()
