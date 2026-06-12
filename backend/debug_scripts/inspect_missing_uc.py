import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from database import get_connection

conn = get_connection()
cursor = conn.cursor()

cursor.execute("""
    SELECT DISTINCT
        aa.to_school,
        aa.major,
        ac.uc_prefix,
        ac.uc_course_number,
        ac.uc_course_title,
        ac.receiving_courses_text,
        ac.cc_prefix,
        ac.cc_course_number,
        ac.cc_course_title,
        ac.requirement_instruction,
        ac.notes
    FROM articulation_courses ac
    JOIN assist_agreements aa
        ON ac.agreement_id = aa.id
    WHERE
        (ac.uc_prefix IS NULL OR ac.uc_prefix = '')
        AND (ac.uc_course_number IS NULL OR ac.uc_course_number = '')
        AND (ac.uc_course_title IS NULL OR ac.uc_course_title = '')
        AND (ac.receiving_courses_text IS NULL OR ac.receiving_courses_text = '')
    ORDER BY
        aa.to_school,
        aa.major,
        ac.cc_prefix,
        ac.cc_course_number
""")

rows = cursor.fetchall()
conn.close()

print(f"Found {len(rows)} rows with truly missing UC requirement info")

for row in rows:
    print(row)
