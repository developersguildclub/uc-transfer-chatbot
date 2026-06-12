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

Be short, direct, and evidence-backed.
Use the chat history for context.
Use retrieved articulation data only when it is provided.
Follow the claim boundary exactly.
Do not infer non-transferability from missing local rows.
When using rows, cite campus, major, and course.
Format with compact paragraphs or bullets.
Say what is uncertain and what detail would resolve it.
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
    message = message.lower()

    for value in values:
        value = value.strip()

        if not value or (skip and value == skip):
            continue

        needle = value.lower()
        index = message.find(needle)
        while index != -1:
            end = index + len(needle)
            before = index == 0 or not message[index - 1].isalnum()
            after = end == len(message) or not message[end].isalnum()
            if before and after:
                matches.append((index, -len(needle), value))
                break
            index = message.find(needle, index + 1)

    if not matches:
        return None

    return min(matches)[2]


def claim_boundary(to_school, major, rows):
    if not rows:
        return "No matching rows were retrieved. You cannot say the course does not transfer. Say no match was found in local data, and that this is not proof of non-transferability."

    if not to_school or not major:
        return "Rows were retrieved. You may say local data has matches and summarize what campuses or requirements appear. Do not imply this proves transferability for every UC campus or major. Mention that exact articulation depends on campus and major."

    return "Rows were retrieved for the requested UC campus and major. You may answer from those rows only."


def articulation_filters_in(message, filter_values):
    filters = {
        "to_school": first_mentioned(filter_values["to_school"], message),
        "major": first_mentioned(filter_values["major"], message),
        "cc_course": first_mentioned(filter_values["cc_course"], message),
    }
    filters["receiving"] = first_mentioned(
        filter_values["receiving"], message, skip=filters["cc_course"]
    )
    return filters


def looks_like_followup(message):
    text = message.lower().strip()
    words = [word.strip("?.!,") for word in text.split()]
    followup_words = {"also", "another", "compare", "it", "that", "those", "them", "they"}
    followup_phrases = ("what about", "how about", "same for", "and for", "does this", "is this")

    return len(words) <= 12 and (
        bool(set(words) & followup_words) or text.startswith(followup_phrases)
    )


def turn_articulation_filters(messages, filter_values):
    latest = messages[-1]["content"]
    filters = articulation_filters_in(latest, filter_values)
    if any(filters.values()) or not looks_like_followup(latest):
        return filters

    for message in reversed(messages[:-1]):
        if message["role"] != "user":
            continue

        previous = articulation_filters_in(message["content"], filter_values)
        for key, value in previous.items():
            if filters[key] is None:
                filters[key] = value

        if any(filters.values()):
            break

    return filters


def question_context_message(latest_message, filters, filter_values):
    if not any(filters.values()):
        context = {
            "claim_boundary": "No articulation rows were retrieved. Answer from chat history and the local data summary only. Ask for campus, major, UC course, or community college course when needed.",
            "local_data_summary": {
                "campuses": sorted(filter_values["to_school"]),
                "sample_majors": sorted(filter_values["major"])[:20],
            },
        }
    else:
        rows = search_articulations(**filters, limit=500)
        context = {
            "claim_boundary": claim_boundary(filters["to_school"], filters["major"], rows),
            "matched_filters": filters,
            "retrieved_row_summary": {
                "row_count": len(rows),
                "campuses": sorted({row[0] for row in rows if row[0]}),
                "majors": sorted({row[1] for row in rows if row[1]})[:20],
            },
            "retrieved_articulation_rows": articulation_rows(rows[:25]),
        }

    return {
        "role": "user",
        "content": f"Student question: {latest_message}\n\nContext:\n{json.dumps(context, indent=2)}",
    }


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

    filter_values = {
        "to_school": get_valid_schools(),
        "major": get_valid_major(),
        "receiving": get_valid_receiving_courses(),
        "cc_course": get_valid_cc_courses(),
    }
    latest_message = messages[-1]["content"]
    filters = turn_articulation_filters(messages, filter_values)
    model_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *messages[:-1],
        question_context_message(latest_message, filters, filter_values),
    ]

    response = get_chat_model().invoke(model_messages)

    return response_text(response)


def stream_ai_response(messages):
    yield get_ai_response(messages)


def response_text(response):
    if isinstance(response.content, str):
        return response.content

    return response.content_blocks[0]["text"]
