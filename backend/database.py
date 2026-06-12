import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TRANSFER_DB_PATH = BASE_DIR / "transfer.db"
APP_DB_PATH = BASE_DIR / "instance" / "app.db"

DB_PATH = TRANSFER_DB_PATH


def get_connection():
    return sqlite3.connect(TRANSFER_DB_PATH)


def get_app_connection():
    APP_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(APP_DB_PATH)


def create_transfer_schema(cursor):
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
        CREATE TABLE IF NOT EXISTS assist_agreement_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            academic_year_id INTEGER,
            sending_institution_id INTEGER,
            receiving_institution_id INTEGER,
            agreement_type TEXT,
            agreement_label TEXT,
            agreement_key TEXT UNIQUE,
            scraped INTEGER DEFAULT 0
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
            requirement_instruction TEXT,
            requirement_category TEXT,
            section_title TEXT,
            notes TEXT,
            receiving_type TEXT,
            receiving_courses_text TEXT,
            FOREIGN KEY (agreement_id) REFERENCES assist_agreements(id)
        )
        """)


SCHEMA_MIGRATIONS = (create_transfer_schema,)


def run_migrations(cursor):
    cursor.execute("PRAGMA user_version")
    version = cursor.fetchone()[0]

    if version > len(SCHEMA_MIGRATIONS):
        raise RuntimeError(f"Database schema version {version} is newer than this code")

    for next_version, migration in enumerate(SCHEMA_MIGRATIONS[version:], start=version + 1):
        migration(cursor)
        cursor.execute(f"PRAGMA user_version = {next_version}")


def setup_database():
    conn = get_connection()
    cursor = conn.cursor()

    run_migrations(cursor)

    cursor.execute(
        """
        INSERT INTO transfer_info (question_keyword, answer)
        SELECT ?, ?
        WHERE NOT EXISTS (
            SELECT 1 FROM transfer_info WHERE question_keyword = ?
        )
    """,
        (
            "gpa",
            "Most UC campuses recommend a competitive GPA, but exact GPA expectations depend on the campus and major.",
            "gpa",
        ),
    )

    conn.commit()
    conn.close()
