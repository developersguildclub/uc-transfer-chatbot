import json
import time

import requests
from database import get_connection, setup_database

BASE_URL = "https://prod.assistng.org/articulation/api/Agreements/Published"

ACADEMIC_YEAR_ID = 76
SENDING_INSTITUTION_ID = 113  # De Anza

RECEIVING_INSTITUTIONS = [
    {"id": 79, "name": "UC Berkeley"},
    {"id": 89, "name": "UC Davis"},
    {"id": 120, "name": "UC Irvine"},
    {"id": 117, "name": "UC Los Angeles"},
    {"id": 132, "name": "UC Merced"},
    {"id": 144, "name": "UC Riverside"},
    {"id": 7, "name": "UC San Diego"},
    {"id": 128, "name": "UC Santa Barbara"},
    {"id": 132, "name": "UC Santa Cruz"},
]

SCHOOLS_TO_RUN = [school["name"] for school in RECEIVING_INSTITUTIONS]

AGREEMENT_TYPES = ["Major"]


def fetch_agreement_keys(receiving_id, sending_id, academic_year_id, agreement_type):
    # Discovery fetches ASSIST agreement keys before full scraping.
    url = f"{BASE_URL}/for/{receiving_id}/to/{sending_id}/in/{academic_year_id}"

    response = requests.get(
        url, params={"types": agreement_type}, headers={"accept": "application/json"}, timeout=30
    )

    print("Fetching keys:", response.url)

    if response.status_code != 200:
        print("Failed:", response.status_code)
        print(response.text)
        return []

    data = response.json()
    result = data.get("result", {})
    reports = result.get("reports", [])

    print(f"Found {len(reports)} reports from ASSIST")

    return reports


def save_agreement_keys(keys, receiving_id, sending_id, academic_year_id, agreement_type):
    # Saved keys let scraper resume without repeating discovery.
    conn = get_connection()
    cursor = conn.cursor()

    saved_count = 0

    for item in keys:
        if isinstance(item, str):
            try:
                item = json.loads(item)
            except Exception:
                print("Skipping unexpected string item:", item)
                continue

        if not isinstance(item, dict):
            print("Skipping unexpected item:", item)
            continue

        agreement_key = item.get("key")
        label = item.get("label")

        if not agreement_key:
            print("Skipping item with no key:", item)
            continue

        cursor.execute(
            """
            INSERT OR IGNORE INTO assist_agreement_keys (
                academic_year_id,
                sending_institution_id,
                receiving_institution_id,
                agreement_type,
                agreement_label,
                agreement_key,
                scraped
            )
            VALUES (?, ?, ?, ?, ?, ?, 0)
        """,
            (academic_year_id, sending_id, receiving_id, agreement_type, label, agreement_key),
        )

        saved_count += cursor.rowcount

    conn.commit()
    conn.close()

    return saved_count


def main():
    # Batch entry point discovers keys for the selected UC campuses.
    setup_database()

    selected_institutions = [
        school for school in RECEIVING_INSTITUTIONS if school["name"] in SCHOOLS_TO_RUN
    ]

    if not selected_institutions:
        print("No schools selected. Check SCHOOLS_TO_RUN names.")
        return

    print("Running selected schools:")
    for school in selected_institutions:
        print(f"- {school['name']}")

    total_saved = 0

    for receiving in selected_institutions:
        for agreement_type in AGREEMENT_TYPES:
            keys = fetch_agreement_keys(
                receiving["id"], SENDING_INSTITUTION_ID, ACADEMIC_YEAR_ID, agreement_type
            )

            saved = save_agreement_keys(
                keys, receiving["id"], SENDING_INSTITUTION_ID, ACADEMIC_YEAR_ID, agreement_type
            )

            total_saved += saved

            print(f"Found {len(keys)} keys for {receiving['name']} {agreement_type}")
            print(f"Saved {saved} new keys")
            print("-" * 60)

            time.sleep(1)

    print(f"Done. Saved {total_saved} new agreement keys.")


if __name__ == "__main__":
    main()
