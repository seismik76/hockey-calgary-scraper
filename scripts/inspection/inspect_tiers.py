
import pandas as pd
from sqlalchemy import create_engine

def inspect_u11_u13_tiers():
    engine = create_engine("sqlite:///hockey_calgary.db")
    
    query = """
    SELECT DISTINCT l.name as League
    FROM leagues l
    WHERE l.name LIKE '%U11%' OR l.name LIKE '%U13%'
    ORDER BY l.name
    """
    
    df = pd.read_sql(query, engine)
    print("--- U11 / U13 Leagues ---")
    for league in df['League']:
        print(league)

if __name__ == "__main__":
    inspect_u11_u13_tiers()
