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
    conn = sqlite3.connect(APP_DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def setup_app_database():
    conn = get_app_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            csrf_token_hash TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            expires_at INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cursor.execute("PRAGMA table_info(sessions)")
    session_columns = {row[1] for row in cursor.fetchall()}
    if "csrf_token_hash" not in session_columns:
        cursor.execute("ALTER TABLE sessions ADD COLUMN csrf_token_hash TEXT")
    cursor.execute("DELETE FROM sessions WHERE csrf_token_hash IS NULL")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversation_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            position INTEGER NOT NULL,
            created_at INTEGER NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
            UNIQUE(conversation_id, position)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS conversations_user_updated_idx
        ON conversations (user_id, updated_at DESC)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS messages_conversation_position_idx
        ON conversation_messages (conversation_id, position)
    """)

    conn.commit()
    conn.close()


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
