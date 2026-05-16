import json
import requests
import time
from database import get_connection, setup_database
from assist_keys import ASSIST_AGREEMENTS

ASSIST_API_URL = "https://prod.assistng.org/articulation/api/Agreements"

def fetch_assist_agreement(key):
    response = requests.get(
        ASSIST_API_URL,
        params={"Key": key},
        headers={"accept": "application/json"}
    )

    print("Fetching:", response.url)

    if response.status_code != 200:
        print("Failed key:", key)
        print("Status:", response.status_code)
        print(response.text)
        return None

    return response.json()

def save_assist_agreement(source_key, metadata, data):
    result = data.get("result", {})

    raw_json = json.dumps(data)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO assist_agreements (
            source_url,
            from_school,
            to_school,
            major,
            academic_year,
            raw_json
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        source_key,
        metadata.get("from_school", "Unknown"),
        metadata.get("to_school", "Unknown"),
        metadata.get("major", result.get("name", "Unknown major")),
        "Unknown year",
        raw_json
    ))

    conn.commit()
    conn.close()

def main():
    setup_database()

    for agreement in ASSIST_AGREEMENTS:
        key = agreement["key"]

        print("\n==============================")
        print("Scraping:", agreement["from_school"], "→", agreement["to_school"], agreement["major"])

        data = fetch_assist_agreement(key)

        if data:
            save_assist_agreement(key, agreement, data)
            print("Saved!")

        time.sleep(1)

if __name__ == "__main__":
    main()