import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "transfer.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def setup_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transfer_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_keyword TEXT,
            answer TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assist_agreements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_url TEXT UNIQUE,
            from_school TEXT,
            to_school TEXT,
            major TEXT,
            academic_year TEXT,
            raw_json TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articulation_courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agreement_id INTEGER,
            uc_prefix TEXT,
            uc_course_number TEXT,
            uc_course_title TEXT,
            cc_prefix TEXT,
            cc_course_number TEXT,
            cc_course_title TEXT,
            group_position INTEGER,
            course_position INTEGER,
            group_conjunction TEXT,
            course_conjunction TEXT,
            notes TEXT,
            FOREIGN KEY (agreement_id) REFERENCES assist_agreements(id)
        )
    """)

    cursor.execute("""
        INSERT INTO transfer_info (question_keyword, answer)
        SELECT ?, ?
        WHERE NOT EXISTS (
            SELECT 1 FROM transfer_info WHERE question_keyword = ?
        )
    """, (
        "gpa",
        "Most UC campuses recommend a competitive GPA, but exact GPA expectations depend on the campus and major.",
        "gpa"
    ))

    conn.commit()
    conn.close()