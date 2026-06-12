import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from database import get_connection

# Debug helper prints rows without explicit requirement instructions.
conn = get_connection()
cursor = conn.cursor()

cursor.execute("""
    SELECT
        aa.to_school,
        aa.major,
        ac.uc_prefix,
        ac.uc_course_number,
        ac.uc_course_title,
        ac.cc_prefix,
        ac.cc_course_number,
        ac.cc_course_title,
        ac.group_conjunction,
        ac.course_conjunction,
        ac.requirement_instruction
    FROM articulation_courses ac
    JOIN assist_agreements aa
        ON ac.agreement_id = aa.id
    WHERE ac.requirement_instruction IS NULL
       OR ac.requirement_instruction = ''
    LIMIT 30
""")

for row in cursor.fetchall():
    print(row)

conn.close()
