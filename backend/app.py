import hashlib
import hmac
import json
import os
import secrets
import time
from sqlite3 import IntegrityError

from database import get_app_connection, setup_app_database, setup_database
from flask import Flask, Response, jsonify, request, stream_with_context
from flask_cors import CORS
from model import get_ai_response
from query_courses import search_articulations
from werkzeug.security import check_password_hash, generate_password_hash

FRONTEND_ORIGINS = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
SESSION_COOKIE_NAME = "uc_transfer_session"
CSRF_COOKIE_NAME = "uc_transfer_csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"
SESSION_TTL_SECONDS = 60 * 60 * 24 * 14
COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "").lower() == "true"

app = Flask(__name__)
CORS(
    app,
    origins=FRONTEND_ORIGINS,
    supports_credentials=True,
    allow_headers=["Content-Type", CSRF_HEADER_NAME],
)

setup_database()
setup_app_database()


@app.route("/")
def index():
    return "Backend is running!"


@app.route("/search", methods=["GET"])
def search():
    try:
        to_school = request.args.get("to_school")
        major = request.args.get("major")
        receiving = request.args.get("receiving")
        cc_course = request.args.get("cc_course")
        limit = request.args.get("limit", default=50, type=int)

        rows = search_articulations(
            to_school=to_school, major=major, receiving=receiving, cc_course=cc_course, limit=limit
        )

        results = []

        for row in rows:
            (
                to_school,
                major,
                academic_year,
                receiving_type,
                receiving_courses_text,
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
                requirement_instruction,
                requirement_category,
                section_title,
                notes,
            ) = row

            results.append(
                {
                    "to_school": to_school,
                    "major": major,
                    "academic_year": academic_year,
                    "receiving_type": receiving_type,
                    "receiving_courses_text": receiving_courses_text,
                    "uc_course": f"{uc_prefix} {uc_course_number}".strip(),
                    "uc_course_title": uc_course_title,
                    "cc_course": f"{cc_prefix} {cc_course_number}".strip(),
                    "cc_course_title": cc_course_title,
                    "group_position": group_position,
                    "course_position": course_position,
                    "group_conjunction": group_conjunction,
                    "course_conjunction": course_conjunction,
                    "requirement_instruction": requirement_instruction,
                    "requirement_category": requirement_category,
                    "section_title": section_title,
                    "notes": notes,
                }
            )

        return jsonify({"count": len(results), "results": results})

    except Exception:
        app.logger.exception("Search request failed")
        return jsonify({"error": "Search request failed"}), 500


def credentials_from_request():
    error = origin_error()
    if error:
        return None, None, error

    data, error = json_body()
    if error:
        return None, None, error

    email = data.get("email")
    password = data.get("password")
    if not isinstance(email, str) or not isinstance(password, str):
        return None, None, None

    return email.strip().lower(), password, None


def origin_error():
    origin = request.headers.get("Origin")
    if origin and origin not in FRONTEND_ORIGINS:
        return jsonify({"error": "Origin not allowed"}), 403

    return None


def json_body():
    if not request.is_json:
        return None, (jsonify({"error": "Expected JSON object"}), 400)

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, (jsonify({"error": "Expected JSON object"}), 400)

    return data, None


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def user_from_row(row):
    return {"id": row[0], "email": row[1]}


def current_session():
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None

    conn = get_app_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT u.id, u.email, s.token_hash, s.csrf_token_hash
        FROM sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.token_hash = ? AND s.expires_at > ?
    """,
        (token_hash(token), int(time.time())),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {"user": user_from_row(row), "token_hash": row[2], "csrf_token_hash": row[3]}


def csrf_matches(session, csrf_token):
    if not csrf_token or not session["csrf_token_hash"]:
        return False

    return hmac.compare_digest(session["csrf_token_hash"], token_hash(csrf_token))


def require_user():
    session = current_session()
    if not session:
        return None, (jsonify({"error": "Authentication required"}), 401)

    return session, None


def require_write_user():
    error = origin_error()
    if error:
        return None, error

    session, error = require_user()
    if error:
        return None, error

    if not csrf_matches(session, request.headers.get(CSRF_HEADER_NAME)):
        return None, (jsonify({"error": "CSRF token required"}), 403)

    return session, None


def set_csrf_cookie(response, csrf_token):
    response.set_cookie(
        CSRF_COOKIE_NAME,
        csrf_token,
        max_age=SESSION_TTL_SECONDS,
        secure=COOKIE_SECURE,
        samesite="Lax",
    )


def response_with_session(user):
    now = int(time.time())
    token = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)

    conn = get_app_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO sessions (user_id, token_hash, csrf_token_hash, created_at, expires_at)
        VALUES (?, ?, ?, ?, ?)
    """,
        (user["id"], token_hash(token), token_hash(csrf_token), now, now + SESSION_TTL_SECONDS),
    )
    conn.commit()
    conn.close()

    response = jsonify({"user": user, "csrfToken": csrf_token})
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=SESSION_TTL_SECONDS,
        secure=COOKIE_SECURE,
        httponly=True,
        samesite="Lax",
    )
    set_csrf_cookie(response, csrf_token)
    return response


@app.route("/auth/signup", methods=["POST"])
def signup():
    # TODO: Add email verification before accounts can own saved conversations.
    # TODO: Add password reset tokens after mail delivery config exists.
    email, password, error = credentials_from_request()
    if error:
        return error

    if not email or not password:
        return jsonify({"error": "Expected email and password"}), 400

    if "@" not in email:
        return jsonify({"error": "Expected a valid email"}), 400

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    now = int(time.time())
    conn = get_app_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO users (email, password_hash, created_at)
            VALUES (?, ?, ?)
        """,
            (email, generate_password_hash(password), now),
        )
        conn.commit()
    except IntegrityError:
        conn.close()
        return jsonify({"error": "An account already exists for that email"}), 409

    user = {"id": cursor.lastrowid, "email": email}
    conn.close()

    return response_with_session(user), 201


@app.route("/auth/login", methods=["POST"])
def login():
    email, password, error = credentials_from_request()
    if error:
        return error

    if not email or not password:
        return jsonify({"error": "Expected email and password"}), 400

    conn = get_app_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, email, password_hash
        FROM users
        WHERE email = ?
    """,
        (email,),
    )
    row = cursor.fetchone()
    conn.close()

    if not row or not check_password_hash(row[2], password):
        return jsonify({"error": "Invalid email or password"}), 401

    return response_with_session(user_from_row(row))


@app.route("/auth/logout", methods=["POST"])
def logout():
    session, error = require_write_user()
    if error:
        return error

    conn = get_app_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE token_hash = ?", (session["token_hash"],))
    conn.commit()
    conn.close()

    response = jsonify({"user": None})
    response.delete_cookie(SESSION_COOKIE_NAME, secure=COOKIE_SECURE, samesite="Lax")
    response.delete_cookie(CSRF_COOKIE_NAME, secure=COOKIE_SECURE, samesite="Lax")
    return response


@app.route("/auth/me", methods=["GET"])
def auth_me():
    session = current_session()
    if not session:
        return jsonify({"user": None, "csrfToken": None})

    csrf_token = request.cookies.get(CSRF_COOKIE_NAME)
    if csrf_matches(session, csrf_token):
        return jsonify({"user": session["user"], "csrfToken": csrf_token})

    csrf_token = secrets.token_urlsafe(32)
    conn = get_app_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE sessions SET csrf_token_hash = ? WHERE token_hash = ?",
        (token_hash(csrf_token), session["token_hash"]),
    )
    conn.commit()
    conn.close()

    response = jsonify({"user": session["user"], "csrfToken": csrf_token})
    set_csrf_cookie(response, csrf_token)
    return response


def conversation_title(text):
    title = " ".join(text.split())
    if len(title) <= 48:
        return title

    return f"{title[:45]}..."


def conversation_from_row(row):
    return {"id": row[0], "title": row[1], "updated_at": row[2]}


def user_conversation(cursor, user_id, conversation_id):
    cursor.execute(
        """
        SELECT id, title, updated_at
        FROM conversations
        WHERE id = ? AND user_id = ?
    """,
        (conversation_id, user_id),
    )
    row = cursor.fetchone()
    if not row:
        return None

    return conversation_from_row(row)


@app.route("/conversations", methods=["GET"])
def conversations():
    session, error = require_user()
    if error:
        return error

    limit = request.args.get("limit", default=100, type=int)
    limit = min(max(limit, 1), 100)

    conn = get_app_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, title, updated_at
        FROM conversations
        WHERE user_id = ?
        ORDER BY updated_at DESC
        LIMIT ?
    """,
        (session["user"]["id"], limit),
    )
    rows = cursor.fetchall()
    conn.close()

    return jsonify({"conversations": [conversation_from_row(row) for row in rows]})


@app.route("/conversations/<int:conversation_id>", methods=["GET"])
def get_conversation(conversation_id):
    session, error = require_user()
    if error:
        return error

    conn = get_app_connection()
    cursor = conn.cursor()
    conversation = user_conversation(cursor, session["user"]["id"], conversation_id)
    if not conversation:
        conn.close()
        return jsonify({"error": "Conversation not found"}), 404

    messages = stored_messages(cursor, conversation_id)
    conn.close()

    return jsonify({"conversation": conversation, "messages": messages})


def stored_messages(cursor, conversation_id):
    cursor.execute(
        """
        SELECT role, content
        FROM conversation_messages
        WHERE conversation_id = ?
        ORDER BY position
    """,
        (conversation_id,),
    )
    return [{"role": row[0], "content": row[1]} for row in cursor.fetchall()]


@app.route("/chat", methods=["POST"])
def chat():
    session, error = require_write_user()
    if error:
        return error

    data, error = json_body()
    if error:
        return error

    message = data.get("message")
    if not isinstance(message, str) or not message.strip():
        return jsonify({"error": "Expected message"}), 400

    message = message.strip()

    conversation_id = data.get("conversation_id")
    if conversation_id is not None and not isinstance(conversation_id, int):
        return jsonify({"error": "Expected conversation_id"}), 400

    conn = get_app_connection()
    cursor = conn.cursor()
    if conversation_id is None:
        prior_messages = []
    else:
        conversation = user_conversation(cursor, session["user"]["id"], conversation_id)
        if not conversation:
            conn.close()
            return jsonify({"error": "Conversation not found"}), 404
        prior_messages = stored_messages(cursor, conversation_id)
    conn.close()

    messages = [*prior_messages, {"role": "user", "content": message}]

    try:
        ai_reply = get_ai_response(messages)
    except Exception:
        app.logger.exception("Chat request failed")
        return jsonify({"error": "Chat request failed"}), 500

    now = int(time.time())
    conn = get_app_connection()
    cursor = conn.cursor()

    if conversation_id is None:
        cursor.execute(
            """
            INSERT INTO conversations (user_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """,
            (session["user"]["id"], conversation_title(message), now, now),
        )
        conversation_id = cursor.lastrowid
        position = 0
    else:
        cursor.execute(
            """
            SELECT COALESCE(MAX(position), -1)
            FROM conversation_messages
            WHERE conversation_id = ?
        """,
            (conversation_id,),
        )
        position = cursor.fetchone()[0] + 1

    cursor.execute(
        """
        UPDATE conversations
        SET updated_at = ?
        WHERE id = ?
    """,
        (now, conversation_id),
    )
    cursor.executemany(
        """
        INSERT INTO conversation_messages (conversation_id, role, content, position, created_at)
        VALUES (?, ?, ?, ?, ?)
    """,
        [
            (conversation_id, "user", message, position, now),
            (conversation_id, "assistant", ai_reply, position + 1, now),
        ],
    )
    conn.commit()
    conn.close()

    def format_sse(event, payload):
        return f"event: {event}\ndata: {json.dumps(payload)}\n\n"

    def generate():
        yield format_sse("message_start", {"conversation_id": conversation_id})
        yield format_sse("text_delta", {"text": ai_reply})
        yield format_sse("message_end", {})

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
