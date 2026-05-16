import json
from database import get_connection, setup_database

def extract_course_name(course):
    prefix = course.get("prefix", "")
    number = course.get("courseNumber", "")
    title = course.get("courseTitle", "")
    return prefix, number, title

def extract_notes(course):
    notes = []

    for attr in course.get("attributes", []):
        content = attr.get("content")
        if content:
            notes.append(content)

    return " | ".join(notes)

def parse_and_save_courses():
    setup_database()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, raw_json
        FROM assist_agreements
        LIMIT 1
    """)

    row = cursor.fetchone()

    if not row:
        print("No ASSIST agreement found.")
        conn.close()
        return

    agreement_id, raw_json = row

    # Clear old parsed rows for this agreement so we do not duplicate data
    cursor.execute("""
        DELETE FROM articulation_courses
        WHERE agreement_id = ?
    """, (agreement_id,))

    data = json.loads(raw_json)
    result = data.get("result", {})

    articulations_raw = result.get("articulations", "[]")
    articulations = json.loads(articulations_raw)

    total_saved = 0

    for section in articulations:
        articulation = section.get("articulation", {})

        uc_course = articulation.get("course", {})
        uc_prefix, uc_number, uc_title = extract_course_name(uc_course)

        sending = articulation.get("sendingArticulation", {})
        course_groups = sending.get("items", [])

        # This tells us if the De Anza groups are OR / AND
        group_conjunction = "Unknown"

        group_conjunctions = sending.get("courseGroupConjunctions", [])
        if group_conjunctions:
            group_conjunction = group_conjunctions[0].get("groupConjunction", "Unknown")

        for group in course_groups:
            group_position = group.get("position", 0)
            course_conjunction = group.get("courseConjunction", "Unknown")
            cc_courses = group.get("items", [])

            for cc_course in cc_courses:
                course_position = cc_course.get("position", 0)
                cc_prefix, cc_number, cc_title = extract_course_name(cc_course)
                notes = extract_notes(cc_course)

                cursor.execute("""
                    INSERT INTO articulation_courses (
                        agreement_id,
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
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    agreement_id,
                    uc_prefix,
                    uc_number,
                    uc_title,
                    cc_prefix,
                    cc_number,
                    cc_title,
                    group_position,
                    course_position,
                    group_conjunction,
                    course_conjunction,
                    notes
                ))

                total_saved += 1

    conn.commit()
    conn.close()

    print(f"Saved {total_saved} articulated course rows.")

if __name__ == "__main__":
    parse_and_save_courses()