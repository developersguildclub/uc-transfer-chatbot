import requests

# Institution helper prints UC ids used by ASSIST discovery.
url = "https://prod.assistng.org/Institutions/api"

response = requests.get(url)
response.raise_for_status()

institutions = response.json()

for school in institutions:
    names = school.get("names", [])

    # Visible names avoid old hidden institution labels.
    visible_names = [n for n in names if not n.get("hideInList", False)]

    if not visible_names:
        continue

    current_name = visible_names[-1].get("name", "")

    # Name filtering is enough for this helper output.
    if "University of California" in current_name or current_name.startswith("UC "):
        print(school["id"], "-", current_name)
