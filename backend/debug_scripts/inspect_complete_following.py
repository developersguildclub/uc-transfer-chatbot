import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from database import get_connection

# Debug helper prints rows with generic completion instructions.
conn = get_connection()
cursor = conn.cursor()

cursor.execute("""
    SELECT
        ac.agreement_id,
        aa.to_school,
        aa.major,
        aa.academic_year,
        ac.receiving_type,
        ac.receiving_courses_text,
        ac.uc_prefix,
        ac.uc_course_number,
        ac.uc_course_title,
        ac.cc_prefix,
        ac.cc_course_number,
        ac.cc_course_title,
        ac.group_conjunction,
        ac.course_conjunction,
        ac.requirement_instruction,
        ac.notes
    FROM articulation_courses ac
    JOIN assist_agreements aa
        ON ac.agreement_id = aa.id
    WHERE ac.requirement_instruction = 'Complete the following'
    ORDER BY
        ac.agreement_id,
        ac.receiving_courses_text,
        ac.group_position,
        ac.course_position
""")

rows = cursor.fetchall()
conn.close()

print(f"Rows with 'Complete the following': {len(rows)}")

for row in rows[:100]:
    (
        agreement_id,
        to_school,
        major,
        academic_year,
        receiving_type,
        receiving_courses_text,
        uc_prefix,
        uc_num,
        uc_title,
        cc_prefix,
        cc_num,
        cc_title,
        group_conj,
        course_conj,
        requirement_instruction,
        notes,
    ) = row

    receiving_side = receiving_courses_text

    if not receiving_side:
        receiving_side = f"{uc_prefix} {uc_num} - {uc_title}".strip(" -")

    print("\n" + "=" * 80)
    print(f"Agreement ID: {agreement_id}")
    print(f"{to_school} | {major} | {academic_year}")
    print(f"Receiving type: {receiving_type}")
    print(f"Receiving side: {receiving_side}")
    print(f"CC course: {cc_prefix} {cc_num} - {cc_title}")
    print(f"Group conjunction: {group_conj}")
    print(f"Course conjunction: {course_conj}")
    print(f"Requirement: {requirement_instruction}")

    if notes:
        print(f"Notes: {notes}")
