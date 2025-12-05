import sqlite3

conn = sqlite3.connect('hockey_calgary.db')
cursor = conn.cursor()

query = """
SELECT t.name, l.name, l.type, s.gp
FROM teams t
JOIN standings s ON t.id = s.team_id
JOIN seasons se ON s.season_id = se.id
JOIN leagues l ON s.league_id = l.id
JOIN communities c ON t.community_id = c.id
WHERE se.name = '2025-2026'
  AND c.name = 'Southwest'
  AND l.name LIKE '%U11%'
"""

cursor.execute(query)
results = cursor.fetchall()

print(f"Total Teams found: {len(results)}")
print("-" * 70)
for row in results:
    print(f"Team: {row[0]} | League: {row[1]} | Type: {row[2]} | GP: {row[3]}")

conn.close()
