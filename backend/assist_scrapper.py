import json
import requests
from database import get_connection, setup_database

ASSIST_URL = "https://prod.assistng.org/articulation/api/Agreements?Key=76%2F113%2Fto%2F79%2FMajor%2F18bc32d8-6aa4-47cc-aced-08ddbf3f4ee7"

def fetch_assist_agreement(url):
    response = requests.get(url, headers={
        "accept": "application/json"
    })

    if response.status_code != 200:
        print("Response text:")
        print(response.text)
        raise Exception(f"Failed to fetch ASSIST data. Status code: {response.status_code}")

    return response.json()

def save_assist_agreement(url, data):
    result = data.get("result", {})

    major = result.get("name", "Unknown major")

    academic_year_raw = result.get("academicYear", "{}")
    academic_year = "Unknown year"

    try:
        academic_year_data = json.loads(academic_year_raw)
        academic_year = academic_year_data.get("code", "Unknown year")
    except Exception:
        pass

    # update these after inspecting the actual response structure
    from_school = "De Anza College"
    to_school = "Unknown UC"

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
        url,
        from_school,
        to_school,
        major,
        academic_year,
        raw_json
    ))

    conn.commit()
    conn.close()

def main():
    setup_database()

    print("Fetching ASSIST agreement...")
    data = fetch_assist_agreement(ASSIST_URL)

    print("Saving agreement to database...")
    save_assist_agreement(ASSIST_URL, data)

    result = data.get("result", {})

    print("\nSaved agreement!")
    print("Major:", result.get("name"))
    print("Type:", result.get("type"))
    print("Publish date:", result.get("publishDate"))

    articulations_raw = result.get("articulations", "[]")

    try:
        articulations = json.loads(articulations_raw)
        print("Number of articulation sections:", len(articulations))
    except Exception as e:
        print("Could not parse articulations.")
        print("Error:", e)

if __name__ == "__main__":
    main()