import requests

url = "https://prod.assistng.org/Institutions/api"

response = requests.get(url)
response.raise_for_status()

institutions = response.json()

for school in institutions:
    names = school.get("names", [])

    # Get the most recent visible name
    visible_names = [n for n in names if not n.get("hideInList", False)]

    if not visible_names:
        continue

    current_name = visible_names[-1].get("name", "")

    # UC schools usually have category/system data,
    # but name filtering is the easiest first pass.
    if "University of California" in current_name or current_name.startswith("UC "):
        print(school["id"], "-", current_name)
