import json
from database import get_connection

conn = get_connection()
cursor = conn.cursor()

cursor.execute("""
    SELECT raw_json
    FROM assist_agreements
    LIMIT 1
""")

row = cursor.fetchone()
conn.close()

if not row:
    print("No ASSIST agreement found.")
    exit()

data = json.loads(row[0])
result = data.get("result", {})

print("Result keys:")
print(result.keys())

print("\nMajor:")
print(result.get("name"))

articulations_raw = result.get("articulations", "[]")
articulations = json.loads(articulations_raw)

print("\nNumber of real articulation sections:")
print(len(articulations))

print("\nFirst articulation keys:")
print(articulations[0].keys())

print("\nFirst articulation preview:")
print(json.dumps(articulations[0], indent=2)[:5000])