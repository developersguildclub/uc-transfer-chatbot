import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from database import get_connection

conn = get_connection()
cursor = conn.cursor()

cursor.execute("""
    SELECT raw_json
    FROM assist_agreements
    WHERE to_school LIKE '%Berkeley%'
      AND major LIKE '%Society and Environment%'
    LIMIT 1
""")

row = cursor.fetchone()
conn.close()

if not row:
    print("No agreement found.")
    exit()

data = json.loads(row[0])
result = data.get("result", {})
articulations = json.loads(result.get("articulations", "[]"))

for i, section in enumerate(articulations):
    articulation = section.get("articulation", {})

    if articulation.get("type") != "Course" and articulation.get("type") != "Series":
        print("=" * 80)
        print("SECTION INDEX:", i)
        print("Articulation type:", articulation.get("type"))
        print("Articulation keys:", articulation.keys())
        print(json.dumps(articulation, indent=2)[:8000])
        break
