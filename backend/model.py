import json
import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from query_courses import (
    get_valid_cc_courses,
    get_valid_major,
    get_valid_receiving_courses,
    get_valid_schools,
    search_articulations,
)

load_dotenv()

chat_model = None

SYSTEM_PROMPT = """
You are a UC transfer advising assistant.

Use only the retrieved articulation rows. Do not use outside knowledge.
The claim boundary is mandatory. Do not contradict it.
Do not answer "yes" or "no" unless the claim boundary says that is allowed.
Do not say a course does not transfer just because no local row was found.
Answer the student's question first, then cite the relevant row details briefly.
Keep the answer concise.
""".strip()


def articulation_rows(rows):
    prompt_rows = []

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

        prompt_rows.append(
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
                "requirement_category": requirement_category,
                "section_title": section_title,
                "notes": notes,
            }
        )

    return prompt_rows


def first_mentioned(values, message, skip=None):
    matches = []

    for value in values:
        value = value.strip()

        if not value or (skip and value == skip):
            continue

        index = message.find(value.lower())
        if index != -1:
            matches.append((index, value))

    if not matches:
        return None

    return min(matches)[1]


def claim_boundary(to_school, major, rows):
    if not rows:
        return "No matching rows were retrieved. You cannot say the course does not transfer. Say no match was found in local data, and that this is not proof of non-transferability."

    if not to_school or not major:
        return "Rows were retrieved. You may say local data has matches and summarize what campuses or requirements appear. Do not imply this proves transferability for every UC campus or major. Mention that exact articulation depends on campus and major."

    return "Rows were retrieved for the requested UC campus and major. You may answer from those rows only."


def get_chat_model():
    global chat_model

    if chat_model is None:
        chat_model = init_chat_model(
            model="gpt-5-mini",
            base_url="https://api.llm7.io/v1"
            if os.getenv("USE_LLM7", "").lower() == "true"
            else None,
            api_key=os.getenv("AI_API_KEY"),
        )

    return chat_model


def get_ai_response(messages):
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]

    filters = {
        "to_school": None,
        "major": None,
        "receiving": None,
        "cc_course": None,
    }
    filter_values = {
        "to_school": get_valid_schools(),
        "major": get_valid_major(),
        "receiving": get_valid_receiving_courses(),
        "cc_course": get_valid_cc_courses(),
    }

    for message in reversed(messages):
        if message["role"] != "user":
            continue

        content = message["content"].lower()

        if filters["to_school"] is None:
            filters["to_school"] = first_mentioned(filter_values["to_school"], content)
        if filters["major"] is None:
            filters["major"] = first_mentioned(filter_values["major"], content)
        if filters["cc_course"] is None:
            filters["cc_course"] = first_mentioned(filter_values["cc_course"], content)
        if filters["receiving"] is None:
            filters["receiving"] = first_mentioned(
                filter_values["receiving"], content, skip=filters["cc_course"]
            )

        if all(filters.values()):
            break

    latest_message = messages[-1]["content"]

    if not any(filters.values()):
        campuses = sorted(get_valid_schools())
        majors = sorted(get_valid_major())[:20]
        model_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *messages[:-1],
            {
                "role": "user",
                "content": "\n\n".join(
                    [
                        f"Student question: {latest_message}",
                        "Claim boundary:",
                        "No specific articulation rows were retrieved because no UC campus, major, UC course, or community college course was detected. You may answer only from the local data summary below. If the student asks a broad question, summarize what local data is available and ask for a more specific campus, major, or course when needed.",
                        "Local data summary:",
                        json.dumps({"campuses": campuses, "sample_majors": majors}, indent=2),
                    ]
                ),
            },
        ]

        response = get_chat_model().invoke(model_messages)

        return response_text(response)

    rows = search_articulations(**filters, limit=500)
    summary = {
        "row_count": len(rows),
        "campuses": sorted({row[0] for row in rows if row[0]}),
        "majors": sorted({row[1] for row in rows if row[1]})[:20],
    }
    model_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *messages[:-1],
        {
            "role": "user",
            "content": "\n\n".join(
                [
                    f"Student question: {latest_message}",
                    "Claim boundary:",
                    claim_boundary(filters["to_school"], filters["major"], rows),
                    "Matched filters:",
                    json.dumps(filters, indent=2),
                    "Retrieved row summary:",
                    json.dumps(summary, indent=2),
                    "Retrieved articulation rows:",
                    json.dumps(articulation_rows(rows[:25]), indent=2),
                ]
            ),
        },
    ]

    response = get_chat_model().invoke(model_messages)

    return response_text(response)


def stream_ai_response(user_message: str):
    yield get_ai_response(user_message)


def response_text(response):
    if isinstance(response.content, str):
        return response.content

    return response.content_blocks[0]["text"]
