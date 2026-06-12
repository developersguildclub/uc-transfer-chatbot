from database import get_connection


def search_articulations(to_school=None, major=None, receiving=None, cc_course=None, limit=50):
    # Search builds one parameterized query across articulation fields.
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
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
            ac.group_position,
            ac.course_position,
            ac.group_conjunction,
            ac.course_conjunction,
            ac.requirement_instruction,
            ac.requirement_category,
            ac.section_title,
            ac.notes
        FROM articulation_courses ac
        JOIN assist_agreements aa
            ON ac.agreement_id = aa.id
        WHERE 1 = 1
    """

    params = []

    if to_school:
        query += " AND aa.to_school LIKE ?"
        params.append(f"%{to_school}%")

    if major:
        query += " AND aa.major LIKE ?"
        params.append(f"%{major}%")

    if receiving:
        query += """
            AND (
                ac.receiving_courses_text LIKE ?
                OR ac.uc_prefix || ' ' || ac.uc_course_number LIKE ?
                OR ac.uc_course_title LIKE ?
            )
        """
        params.extend([f"%{receiving}%", f"%{receiving}%", f"%{receiving}%"])

    if cc_course:
        query += """
            AND (
                ac.cc_prefix || ' ' || ac.cc_course_number LIKE ?
                OR ac.cc_course_title LIKE ?
            )
        """
        params.extend([f"%{cc_course}%", f"%{cc_course}%"])

    query += """
        ORDER BY
            aa.to_school,
            aa.major,
            ac.receiving_courses_text,
            ac.group_position,
            ac.course_position
        LIMIT ?
    """

    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return rows


def get_valid_schools():
    # Valid-value helpers support model-side mention matching.
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT to_school
        FROM assist_agreements WHERE to_school IS NOT NULL 
    """)

    rows = cursor.fetchall()

    conn.close()

    return [row[0] for row in rows]


def get_valid_major():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT major
        FROM assist_agreements WHERE major IS NOT NULL
    """)

    rows = cursor.fetchall()

    conn.close()

    return [row[0] for row in rows]


def get_valid_receiving_courses():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT
        uc_prefix || ' ' || uc_course_number
        FROM articulation_courses
        WHERE uc_prefix IS NOT NULL
        AND uc_course_number IS NOT NULL
    """)
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]


def get_valid_cc_courses():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT
        cc_prefix || ' ' || cc_course_number
        FROM articulation_courses
        WHERE cc_prefix IS NOT NULL
        AND cc_course_number IS NOT NULL
    """)
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]
