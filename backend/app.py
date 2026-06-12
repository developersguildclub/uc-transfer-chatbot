import json

from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from model import stream_ai_response
from database import setup_database
from query_courses import search_articulations

app = Flask(__name__)
CORS(app)

setup_database()

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
            to_school=to_school,
            major=major,
            receiving=receiving,
            cc_course=cc_course,
            limit=limit
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
                notes
            ) = row

            results.append({
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
                "notes": notes
            })

        return jsonify({
            "count": len(results),
            "results": results
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data["message"]

    def format_sse(event, payload):
        return f"event: {event}\ndata: {json.dumps(payload)}\n\n"

    def generate():
        yield format_sse("message_start", {})

        for chunk in stream_ai_response(user_message):
            yield format_sse("text_delta", {"text": chunk})

        yield format_sse("message_end", {})
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Expected JSON object"}), 400

    messages = chat_messages_from_request(data)
    if not messages or messages[-1]["role"] != "user":
        return jsonify({"error": "Expected latest user message"}), 400

    ai_reply = get_ai_response(messages)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache"}
    )

def chat_messages_from_request(data):
    raw_messages = data.get("messages")
    messages = []

    if isinstance(raw_messages, list):
        for item in raw_messages:
            if not isinstance(item, dict):
                continue

            role = item.get("role")
            content = item.get("content")
            if content is None:
                content = item.get("text")

            if role == "bot":
                role = "assistant"

            if role in ("user", "assistant") and isinstance(content, str) and content.strip():
                messages.append({"role": role, "content": content.strip()})

    for index, message in enumerate(messages):
        if message["role"] == "user":
            return messages[index:]

    message = data.get("message")
    if isinstance(message, str) and message.strip():
        return [{"role": "user", "content": message.strip()}]

    return []

if __name__ == "__main__":
    app.run(debug=True, port=5000)
