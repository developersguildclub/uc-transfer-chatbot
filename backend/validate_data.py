from database import get_connection

# Validation script prints parser coverage and suspicious row groups.
conn = get_connection()
cursor = conn.cursor()


def print_count(label, query):
    cursor.execute(query)
    count = cursor.fetchone()[0]
    print(f"{label}: {count}")


def print_group_counts(title, query):
    print(f"\n{title}")
    cursor.execute(query)
    rows = cursor.fetchall()

    for value, count in rows:
        value = value if value else "(blank)"
        print(f"  {value}: {count}")


def print_samples(title, query, params=None, limit=10):
    print(f"\n{title}")

    if params is None:
        params = []

    if "limit" not in query.lower():
        query += "\nLIMIT ?"
        params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()

    if not rows:
        print("  None")
        return

    for row in rows:
        print(" ", row)


print("=== Data Validation Summary ===")

print_count(
    "Rows with missing receiving side",
    """
    SELECT COUNT(*)
    FROM articulation_courses
    WHERE 
        (uc_prefix IS NULL OR uc_prefix = '')
        AND (uc_course_number IS NULL OR uc_course_number = '')
        AND (receiving_courses_text IS NULL OR receiving_courses_text = '')
        AND (uc_course_title IS NULL OR uc_course_title = '')
    """,
)

print_count(
    "Rows with missing CC course",
    """
    SELECT COUNT(*)
    FROM articulation_courses
    WHERE cc_prefix IS NULL
       OR cc_prefix = ''
       OR cc_course_number IS NULL
       OR cc_course_number = ''
    """,
)

print_count(
    "Rows with unknown year",
    """
    SELECT COUNT(*)
    FROM assist_agreements
    WHERE academic_year IS NULL
       OR academic_year = ''
       OR academic_year = 'Unknown year'
    """,
)

print_count(
    "Rows without explicit requirement instruction",
    """
    SELECT COUNT(*)
    FROM articulation_courses
    WHERE requirement_instruction IS NULL
       OR requirement_instruction = ''
    """,
)

print_group_counts(
    "Rows by receiving_type:",
    """
    SELECT receiving_type, COUNT(*)
    FROM articulation_courses
    GROUP BY receiving_type
    ORDER BY COUNT(*) DESC
    """,
)

print_group_counts(
    "Rows by requirement_category:",
    """
    SELECT requirement_category, COUNT(*)
    FROM articulation_courses
    GROUP BY requirement_category
    ORDER BY COUNT(*) DESC
    """,
)

print_group_counts(
    "Agreements by UC campus:",
    """
    SELECT to_school, COUNT(*)
    FROM assist_agreements
    GROUP BY to_school
    ORDER BY COUNT(*) DESC
    """,
)

print_samples(
    "Sample rows with unknown requirement_category:",
    """
    SELECT
        aa.to_school,
        aa.major,
        aa.academic_year,
        ac.receiving_type,
        ac.receiving_courses_text,
        ac.cc_prefix,
        ac.cc_course_number,
        ac.cc_course_title,
        ac.requirement_instruction,
        ac.requirement_category,
        ac.section_title
    FROM articulation_courses ac
    JOIN assist_agreements aa
        ON ac.agreement_id = aa.id
    WHERE ac.requirement_category IS NULL
       OR ac.requirement_category = ''
       OR ac.requirement_category = 'unknown'
    """,
)

print_samples(
    "Sample rows with unknown requirement_category:",
    """
    SELECT
        aa.to_school,
        aa.major,
        aa.academic_year,
        ac.receiving_type,
        ac.receiving_courses_text,
        ac.cc_prefix,
        ac.cc_course_number,
        ac.cc_course_title,
        ac.requirement_instruction,
        ac.requirement_category,
        ac.section_title
    FROM articulation_courses ac
    JOIN assist_agreements aa
        ON ac.agreement_id = aa.id
    WHERE ac.requirement_category IS NULL
       OR ac.requirement_category = ''
       OR ac.requirement_category = 'unknown'
    LIMIT 2
    """,
)

conn.close()
