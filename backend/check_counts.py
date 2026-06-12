from database import get_connection

conn = get_connection()
cursor = conn.cursor()

cursor.execute("""
    SELECT COUNT(*)
    FROM assist_agreement_keys
    WHERE scraped = 0
""")
unscraped = cursor.fetchone()[0]

print("Unscraped agreement keys:", unscraped)

cursor.execute("SELECT COUNT(*) FROM assist_agreement_keys")
print("Total agreement keys:", cursor.fetchone()[0])

cursor.execute("SELECT COUNT(*) FROM assist_agreements")
print("Scraped agreements:", cursor.fetchone()[0])

cursor.execute("SELECT COUNT(*) FROM articulation_courses")
print("Parsed articulation rows:", cursor.fetchone()[0])

conn.close()
