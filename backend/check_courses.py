from database import get_connection

# Course helper prints one major in ASSIST option-group shape.
conn = get_connection()
cursor = conn.cursor()

cursor.execute(
    """
    SELECT
        ac.agreement_id,
        aa.to_school,
        aa.major,
        aa.academic_year,
        ac.uc_prefix,
        ac.uc_course_number,
        ac.uc_course_title,
        ac.receiving_type,
        ac.receiving_courses_text,
        ac.cc_prefix,
        ac.cc_course_number,
        ac.cc_course_title,
        ac.group_position,
        ac.course_position,
        ac.group_conjunction,
        ac.course_conjunction,
        ac.requirement_instruction,
        ac.notes
    FROM articulation_courses ac
    JOIN assist_agreements aa
        ON ac.agreement_id = aa.id
    WHERE aa.to_school LIKE ?
      AND aa.major LIKE ?
    ORDER BY
        ac.agreement_id,
        ac.uc_prefix,
        ac.uc_course_number,
        ac.group_position,
        ac.course_position
""",
    ("%Irvine%", "%Computer Science%"),
)

rows = cursor.fetchall()
conn.close()

current_course_key = None
current_group_key = None

current_course_key = None
current_group_key = None
printed_notes = set()
seen_rows = set()

for row in rows:
    (
        agreement_id,
        to_school,
        major,
        academic_year,
        uc_prefix,
        uc_num,
        uc_title,
        receiving_type,
        receiving_courses_text,
        cc_prefix,
        cc_num,
        cc_title,
        group_pos,
        course_pos,
        group_conj,
        course_conj,
        requirement_instruction,
        notes,
    ) = row

    row_key = (
        agreement_id,
        uc_prefix,
        uc_num,
        uc_title,
        receiving_courses_text,
        cc_prefix,
        cc_num,
        cc_title,
        group_pos,
        course_pos,
    )

    if row_key in seen_rows:
        continue

    seen_rows.add(row_key)

    course_key = (agreement_id, uc_prefix, uc_num, uc_title, receiving_courses_text)

    group_key = (agreement_id, uc_prefix, uc_num, receiving_courses_text, group_pos)

    if course_key != current_course_key:
        print()
        print("=" * 70)
        print(f"{to_school} | {major} | {academic_year or 'Unknown year'}")

        if receiving_courses_text:
            print(f"UC Requirement: {receiving_courses_text}")
        else:
            print(f"UC Requirement: {uc_prefix} {uc_num} - {uc_title}")

        if receiving_type:
            print(f"  Type: {receiving_type}")

        if requirement_instruction:
            print(f"  Requirement: {requirement_instruction}")

        current_course_key = course_key
        current_group_key = None

    if group_key != current_group_key:
        if current_group_key is not None and group_conj:
            print(f"  {group_conj}")

        print(f"  Option {group_pos + 1}:")
        current_group_key = group_key

    prefix_word = "    "
    if course_pos > 0 and course_conj:
        prefix_word = f"    {course_conj} "

    if cc_prefix or cc_num or cc_title:
        course_text = f"{cc_prefix or ''} {cc_num or ''} - {cc_title or ''}".strip()
        print(f"{prefix_word}{course_text}")
    else:
        print(f"{prefix_word}No Course Articulated")

    if notes:
        note_key = (agreement_id, uc_prefix, uc_num, receiving_courses_text, group_pos, notes)

        if note_key not in printed_notes:
            print(f"    Note: {notes}")
            printed_notes.add(note_key)
