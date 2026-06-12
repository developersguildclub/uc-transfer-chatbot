from query_courses import search_articulations

# Query smoke helper checks one course lookup manually.
rows = search_articulations(cc_course="ENGL C1000", limit=10)

print("Number of rows:", len(rows))

for row in rows:
    print(row)
