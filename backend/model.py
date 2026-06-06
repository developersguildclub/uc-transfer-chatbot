import sqlite3
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

def stream_ai_response(user_message: str):
    stream = agent.stream_events(
        {"messages": [
            {"role": "user", "content": user_message}
        ]},
        version="v3"
    )

    for message in stream.messages:
        for delta in message.text:
            if delta:
                yield delta

def get_ai_response(user_message: str):
    message = user_message.lower()
    to_school = None
    major = None
    receiving = None
    cc_course = None

    for school in get_valid_schools():
        if school.lower() in message:
            to_school = school
            break
    
    for major in get_valid_major():
        if major.lower() in message:
            major = major
            break
    
    for receiving in get_valid_receiving_courses():
        if receiving.lower() in message:
            receiving = receiving
            break
    
    for course in get_valid_cc_courses():
        if course.lower() in message:
            cc_course = course
            break

              
    rows = search_articulations(to_school=to_school, major=major, receiving=receiving, cc_course=cc_course)
    print(rows)
if __name__ == "__main__":

    response = get_ai_response(

        "Does CIS 22A transfer to UC Berkeley for Computer Science?"

    )

    print(response)
    """ result = agent.invoke(
        {"messages": [
            {"role": "user", "content": user_message}
        ]}
    )

    return result["messages"][-1].content_blocks[0]["text"]
    """
    """
    # for now

    conn = sqlite3.connect("transfer.db")
    cursor = conn.cursor()

    cursor.execute(\"\"\"
        SELECT answer FROM transfer_info
        WHERE ? LIKE '%' || question_keyword || '%'
        LIMIT 1
    \"\"\", (user_message.lower(),))

    result = cursor.fetchone()
    conn.close()

    if result:
        return result[0]

    return "I do not have information about that yet."
    """
