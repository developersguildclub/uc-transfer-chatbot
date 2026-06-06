from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
import os
from dotenv import load_dotenv
from query_courses import search_articulations, get_valid_schools, get_valid_major, get_valid_receiving_courses, get_valid_cc_courses 


load_dotenv()

llm = init_chat_model(
    model="gpt-5-mini",
    # env files don't support booleans (so we need to check with string)
    base_url="https://api.llm7.io/v1" if os.getenv("USE_LLM7").lower() == "true" else None,
    api_key=os.getenv("AI_API_KEY"),
)

agent = create_agent(
    model=llm,
    system_prompt="You are a helpful assistant",
)

def get_ai_response(messages):
    to_school = None
    major = None
    receiving = None
    cc_course = None

    schools = get_valid_schools()
    majors = get_valid_major()
    receiving_courses = get_valid_receiving_courses()
    cc_courses = get_valid_cc_courses()

    for message in reversed(messages):
        if message["role"] != "user":
            continue

        content = message["content"].lower()

        if to_school is None:
            to_school = first_matching_value(schools, content)
        if major is None:
            major = first_matching_value(majors, content)
        if receiving is None:
            receiving = first_matching_value(receiving_courses, content)
        if cc_course is None:
            cc_course = first_matching_value(cc_courses, content)

    rows = []
    if to_school or major or receiving or cc_course:
        rows = search_articulations(
            to_school=to_school,
            major=major,
            receiving=receiving,
            cc_course=cc_course,
            limit=20
        )

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
