import json
import os
from functools import lru_cache
from pathlib import Path

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
BASE_DIR = Path(__file__).resolve().parent
TRANSFER_REQUIREMENTS_PATH = BASE_DIR / "data" / "transfer_requirements.json"
RECENT_MESSAGE_COUNT = 8
PRIOR_QUESTION_COUNT = 16

SYSTEM_PROMPT = """
You are a UC transfer advising assistant.

Be short, direct, and evidence-backed.
Use the chat history for context.
Use retrieved articulation data only when it is provided.
Use retrieved general education data only when it is provided.
Follow the claim boundary exactly.
Do not infer non-transferability from missing local rows.
When using retrieved data, cite campus, major, course, source, or page when available.
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


@lru_cache
def transfer_requirements():
    with TRANSFER_REQUIREMENTS_PATH.open() as file:
        return json.load(file)["programs"]


def transfer_program_ids(message):
    text = message.lower()
    compact = text.replace("-", "").replace(" ", "")
    program_ids = []

    if "igetc" in compact:
        program_ids.append("igetc")
    if "calgetc" in compact:
        program_ids.append("cal_getc")

    if program_ids:
        return program_ids

    ge_terms = (
        "general education",
        "ge pattern",
        "ge requirements",
        "breadth",
        "ethnic studies",
        "oral communication",
        "critical thinking",
        "ap exam",
        "ap score",
        "partial certification",
    )
    if any(term in text for term in ge_terms):
        return ["igetc", "cal_getc"]

    return []


def transfer_program_context(message):
    program_ids = set(transfer_program_ids(message))
    if not program_ids:
        return None

    programs = []
    for program in transfer_requirements():
        if program["id"] in program_ids:
            programs.append(program)

    return programs


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


def wants_local_summary(message):
    text = message.lower()
    return (
        ("uc" in text and any(word in text for word in ("campus", "campuses", "college", "school")))
        or "what majors" in text
        or "list the uc" in text
    )


def model_history(messages):
    history = messages[:-1]
    if len(history) <= RECENT_MESSAGE_COUNT:
        return history

    questions = [
        message["content"].strip()
        for message in history
        if message["role"] == "user" and message["content"].strip()
    ]
    memory = {
        "omitted_message_count": len(history) - RECENT_MESSAGE_COUNT,
        "recent_user_questions": questions[-PRIOR_QUESTION_COUNT:],
    }

    return [
        {
            "role": "system",
            "content": f"Earlier conversation index:\n{json.dumps(memory, indent=2)}",
        },
        *history[-RECENT_MESSAGE_COUNT:],
    ]


def question_context_message(latest_message, filters, filter_values, program_context):
    if not any(filters.values()):
        context = {
            "claim_boundary": "No articulation rows were retrieved. Answer from chat history and retrieved general education data if present. Ask for campus, major, UC course, community college course, IGETC, or Cal-GETC when needed.",
        }
        if wants_local_summary(latest_message):
            context["local_data_summary"] = {
                "campuses": sorted(filter_values["to_school"]),
                "sample_majors": sorted(filter_values["major"])[:20],
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

    if program_context:
        context["retrieved_general_education"] = program_context

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
    program_context = transfer_program_context(latest_message)
    model_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *model_history(messages),
        question_context_message(latest_message, filters, filter_values, program_context),
    ]

    response = get_chat_model().invoke(model_messages)

    return response_text(response)


def stream_ai_response(messages):
    yield get_ai_response(messages)


def response_text(response):
    if isinstance(response.content, str):
        return response.content

    return response.content_blocks[0]["text"]
