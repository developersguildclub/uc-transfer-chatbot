from database import get_connection

conn = get_connection()
cursor = conn.cursor()

cursor.execute("""
    SELECT
        uc_prefix,
        uc_course_number,
        uc_course_title,
        cc_prefix,
        cc_course_number,
        cc_course_title,
        group_position,
        course_position,
        group_conjunction,
        course_conjunction,
        notes
    FROM articulation_courses
    ORDER BY uc_prefix, uc_course_number, group_position, course_position
""")

rows = cursor.fetchall()
conn.close()

current_uc = None
current_group = None

for row in rows:
    (
        uc_prefix,
        uc_num,
        uc_title,
        cc_prefix,
        cc_num,
        cc_title,
        group_pos,
        course_pos,
        group_conj,
        course_conj,
        notes
    ) = row

    uc_key = f"{uc_prefix} {uc_num} - {uc_title}"

    if uc_key != current_uc:
        print()
        print(uc_key)
        current_uc = uc_key
        current_group = None

    if group_pos != current_group:
        if current_group is not None:
            print(f"  {group_conj}")
        print(f"  Option {group_pos + 1}:")
        current_group = group_pos

    prefix_word = "    "
    if course_pos > 0:
        prefix_word = f"    {course_conj} "

    print(f"{prefix_word}{cc_prefix} {cc_num} - {cc_title}")

    if notes:
        print(f"    Note: {notes}")