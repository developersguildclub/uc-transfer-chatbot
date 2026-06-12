import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from database import get_connection

# Debug helper checks whether parsed wording exists in raw JSON.
conn = get_connection()
cursor = conn.cursor()

cursor.execute("""
    SELECT DISTINCT
        aa.id,
        aa.to_school,
        aa.major,
        aa.raw_json
    FROM assist_agreements aa
    JOIN articulation_courses ac
        ON aa.id = ac.agreement_id
    WHERE ac.requirement_instruction = 'Complete the following'
""")

agreements = cursor.fetchall()
conn.close()

for agreement_id, to_school, major, raw_json in agreements:
    data = json.loads(raw_json)
    raw_text = json.dumps(data)

    found = "Complete the following" in raw_text

    print("\n" + "=" * 80)
    print(f"Agreement ID: {agreement_id}")
    print(f"{to_school} | {major}")
    print("Found exact phrase in raw ASSIST JSON:", found)
