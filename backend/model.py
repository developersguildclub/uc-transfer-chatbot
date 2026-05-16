import sqlite3

def get_ai_response(user_message):
    conn = sqlite3.connect("transfer.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT answer FROM transfer_info
        WHERE ? LIKE '%' || question_keyword || '%'
        LIMIT 1
    """, (user_message.lower(),))

    result = cursor.fetchone()
    conn.close()

    if result:
        return result[0]

    return "I do not have information about that yet."