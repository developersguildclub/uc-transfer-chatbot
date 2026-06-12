import json
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from query_courses import (
    search_articulations,
    get_valid_schools,
    get_valid_major,
    get_valid_receiving_courses,
    get_valid_cc_courses
)


load_dotenv()

chat_model = init_chat_model(
    model="gpt-5-mini",
    base_url="https://api.llm7.io/v1" if os.getenv("USE_LLM7").lower() == "true" else None,
    api_key=os.getenv("AI_API_KEY"),
)

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
            notes
        ) = row

        prompt_rows.append({
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
            "notes": notes
        })

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


def get_ai_response(user_message: str):
    message = user_message.lower()
    to_school = first_mentioned(get_valid_schools(), message)
    major = first_mentioned(get_valid_major(), message)
    cc_course = first_mentioned(get_valid_cc_courses(), message)
    receiving = first_mentioned(get_valid_receiving_courses(), message, skip=cc_course)

    if not any([to_school, major, receiving, cc_course]):
        return "I need a UC campus, major, UC course, or community college course to search the articulation data."

    rows = search_articulations(
        to_school=to_school,
        major=major,
        receiving=receiving,
        cc_course=cc_course,
        limit=500
    )
    summary = {
        "row_count": len(rows),
        "campuses": sorted({row[0] for row in rows if row[0]}),
        "majors": sorted({row[1] for row in rows if row[1]})[:20]
    }

    response = chat_model.invoke([
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": "\n\n".join([
                f"Student question: {user_message}",
                "Claim boundary:",
                claim_boundary(to_school, major, rows),
                "Matched filters:",
                json.dumps({
                    "to_school": to_school,
                    "major": major,
                    "receiving": receiving,
                    "cc_course": cc_course
                }, indent=2),
                "Retrieved row summary:",
                json.dumps(summary, indent=2),
                "Retrieved articulation rows:",
                json.dumps(articulation_rows(rows[:25]), indent=2)
            ])
        }
    ])

    return response.content
def get_ai_response(messages):
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

        for name, values in filter_values.items():
            if filters[name] is None:
                filters[name] = first_matching_value(values, content)

        if all(filters.values()):
            break

    rows = []
    if any(filters.values()):
        rows = search_articulations(**filters, limit=20)

    model_messages = messages
    if rows:
        model_messages = messages[:-1] + [{
            "role": "user",
            "content": f"{messages[-1]['content']}\n\nRelevant articulation rows:\n{format_articulation_rows(rows)}"
        }]

    result = agent.invoke({"messages": model_messages})
    reply = result["messages"][-1]

    if isinstance(reply.content, str):
        return reply.content

    return reply.content_blocks[0]["text"]

def first_matching_value(values, content):
    for value in values:
        if value and value.lower() in content:
            return value

    return None

def format_articulation_rows(rows):
    lines = []

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

        uc_course = " ".join(part for part in [uc_prefix, uc_course_number] if part)
        cc_course = " ".join(part for part in [cc_prefix, cc_course_number] if part)
        receiving_label = receiving_courses_text or uc_course or uc_course_title
        cc_label = " - ".join(part for part in [cc_course, cc_course_title] if part)

        lines.append(
            f"- {to_school}, {major}, {academic_year}: {receiving_label} -> {cc_label}"
        )

    return "\n".join(lines)
