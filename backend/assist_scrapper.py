import json
import time

import requests
from database import get_connection, setup_database

ASSIST_API_URL = "https://prod.assistng.org/articulation/api/Agreements"


def fetch_assist_agreement(key):
    # Scraper fetches full ASSIST agreement JSON for stored keys.
    response = requests.get(
        ASSIST_API_URL, params={"Key": key}, headers={"accept": "application/json"}
    )

    print("Fetching:", response.url)

    if response.status_code != 200:
        print("Failed key:", key)
        print("Status:", response.status_code)
        print(response.text)
        return None

    return response.json()


def parse_json_field(value):
    # ASSIST sometimes returns nested objects as JSON strings.
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return None

    return value


def extract_school_name(result, field_name):
    # School name extraction normalizes ASSIST institution payloads.
    school_raw = result.get(field_name)
    school_data = parse_json_field(school_raw)

    if not isinstance(school_data, dict):
        return "Unknown school"

    names = school_data.get("names", [])

    if names and isinstance(names, list):
        return names[0].get("name", "Unknown school")

    return school_data.get("name", "Unknown school")


def extract_academic_year(result):
    # Academic year extraction keeps readable labels in agreement rows.
    academic_year_raw = result.get("academicYear")
    academic_year_data = parse_json_field(academic_year_raw)

    if isinstance(academic_year_data, dict):
        return (
            academic_year_data.get("code")
            or academic_year_data.get("displayName")
            or academic_year_data.get("name")
            or "Unknown year"
        )

    return "Unknown year"


def save_assist_agreement(source_key, data):
    # Saved agreements keep raw JSON so parsing can improve later.
    result = data.get("result", {})

    from_school = extract_school_name(result, "sendingInstitution")
    to_school = extract_school_name(result, "receivingInstitution")
    major = result.get("name", "Unknown major")
    academic_year = extract_academic_year(result)

    raw_json = json.dumps(data)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO assist_agreements (
            source_url,
            from_school,
            to_school,
            major,
            academic_year,
            raw_json
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (source_key, from_school, to_school, major, academic_year, raw_json),
    )

    cursor.execute(
        """
        UPDATE assist_agreement_keys
        SET scraped = 1
        WHERE agreement_key = ?
    """,
        (source_key,),
    )

    conn.commit()
    conn.close()


def get_unscraped_keys(limit=50):
    # Scraper batches only agreement keys not marked scraped.
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT agreement_key
        FROM assist_agreement_keys
        WHERE scraped = 0
        LIMIT ?
    """,
        (limit,),
    )

    rows = cursor.fetchall()
    conn.close()

    return [row[0] for row in rows]


def main():
    # Batch entry point sleeps between ASSIST requests.
    setup_database()

    keys = get_unscraped_keys(limit=50)

    if not keys:
        print("No unscraped keys found. Run discover_assist_keys.py first.")
        return

    print(f"Scraping {len(keys)} agreements...")

    for key in keys:
        data = fetch_assist_agreement(key)

        if data:
            save_assist_agreement(key, data)
            print("Saved:", key)

        time.sleep(1)

    print("Done scraping batch.")


if __name__ == "__main__":
    main()
