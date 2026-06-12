# UC Transfer Chatbot Backend

This backend powers the **UC Transfer Chatbot**. It fetches and stores ASSIST.org agreement data, parses articulation information into searchable SQLite rows, and provides API endpoints that the frontend and chatbot can use.

## What This Backend Does

- Fetches ASSIST.org agreement keys
- Scrapes full ASSIST agreement JSON
- Stores raw agreement data in SQLite
- Parses UC articulation data into searchable course rows
- Preserves ASSIST `AND` / `OR` course-group logic
- Provides Flask API endpoints for search and chat
- Supports future AI responses using parsed transfer data

## Tech Stack

- Python
- Flask
- SQLite
- ASSIST.org API

---

## Backend Folder Structure

```txt
backend/
  app.py
  database.py
  model.py
  query_courses.py

  discover_assist_keys.py
  assist_scraper.py
  parse_assist.py
  validate_data.py

  check_courses.py
  test_query.py
  transfer.db
  README.md

  debug_scripts/
    inspect_assist.py
    inspect_blank_uc.py
    inspect_complete_following.py
    inspect_missing_receiving_side.py
    inspect_requirement_type.py
    inspect_unknown_requirements.py
    verify_complete_following_source.py
```

---

## Main Backend Files

### `app.py`

The main Flask server. It connects the frontend, database search logic, and chatbot/model response logic.

Current routes:

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/` | Basic health check to confirm the backend is running |
| `GET` | `/search` | Searches parsed ASSIST articulation data from SQLite |
| `POST` | `/chat` | Receives a chatbot message from the frontend and returns a model response |

#### `GET /`

Health-check route.

Example:

```txt
http://127.0.0.1:5000/
```

Returns:

```txt
Backend is running!
```

#### `GET /search`

Searches parsed articulation data from the SQLite database.

Example:

```txt
http://127.0.0.1:5000/search?to_school=Berkeley&major=Aerospace&receiving=Reading&limit=10
```

Supported query parameters:

| Parameter | Meaning | Example |
|---|---|---|
| `to_school` | UC campus name | `Berkeley`, `Davis`, `Irvine` |
| `major` | Major name | `Computer Science`, `Aerospace` |
| `receiving` | UC-side course, series, requirement, or breadth area | `MATH 54`, `Reading` |
| `cc_course` | De Anza course | `CIS 22C`, `MATH 1A` |
| `limit` | Maximum number of rows returned | `10` |

#### `POST /chat`

Receives a frontend chatbot message and sends it to `model.py`.

Example request body:

```json
{
  "message": "What De Anza courses satisfy UC Berkeley MATH 54?"
}
```

---

### `database.py`

Defines the SQLite database connections and creates the transfer-data tables.

Database targets:

```txt
transfer.db          # transfer and articulation seed data
instance/app.db      # private app data, such as accounts and saved chats
```

Transfer-data tables:

| Table | Purpose |
|---|---|
| `transfer_info` | Small test table used for early chatbot testing |
| `assist_agreement_keys` | Stores agreement keys discovered from ASSIST |
| `assist_agreements` | Stores raw full agreement JSON from ASSIST |
| `articulation_courses` | Stores parsed articulation rows for search |

#### `assist_agreement_keys`

Stores agreement keys discovered from ASSIST.

Important columns:

| Column | Meaning |
|---|---|
| `academic_year_id` | ASSIST academic year ID |
| `sending_institution_id` | Community college ID, such as De Anza |
| `receiving_institution_id` | UC campus ID |
| `agreement_type` | Type of agreement, such as `Major` |
| `agreement_label` | Human-readable agreement label |
| `agreement_key` | Full ASSIST agreement key |
| `scraped` | Tracks whether the full agreement JSON has been fetched |

#### `assist_agreements`

Stores raw full agreement data from ASSIST.

Important columns:

| Column | Meaning |
|---|---|
| `source_url` | ASSIST API URL used to fetch the agreement |
| `from_school` | Sending institution, usually De Anza College |
| `to_school` | Receiving UC campus |
| `major` | Major name |
| `academic_year` | Academic year |
| `raw_json` | Full raw JSON response from ASSIST |

> `raw_json` is important because it lets us improve the parser and re-parse data later without scraping ASSIST again.

#### `articulation_courses`

Stores parsed articulation rows.

Important columns:

| Column | Meaning |
|---|---|
| `agreement_id` | Links row back to `assist_agreements` |
| `receiving_type` | UC-side type: `Course`, `Series`, `GeneralEducation`, or `Requirement` |
| `receiving_courses_text` | Human-readable UC-side course/requirement text |
| `uc_prefix` | UC course prefix, such as `MATH` |
| `uc_course_number` | UC course number, such as `54` |
| `uc_course_title` | UC course title |
| `cc_prefix` | De Anza course prefix, such as `MATH` |
| `cc_course_number` | De Anza course number |
| `cc_course_title` | De Anza course title |
| `group_position` | Position of an ASSIST option group |
| `course_position` | Position of a course inside a group |
| `group_conjunction` | Relationship between groups, usually `And` or `Or` |
| `course_conjunction` | Relationship between courses in a group, usually `And` or `Or` |
| `requirement_instruction` | Explicit/generated instruction like “Choose one option” |
| `requirement_category` | Conservative category such as `required_for_admission` or `unknown` |
| `section_title` | ASSIST section or subsection title |
| `notes` | Course-level or section-level notes |

---

## ASSIST Data Pipeline

The data pipeline has three main steps:

```txt
discover_assist_keys.py
        ↓
assist_scraper.py
        ↓
parse_assist.py
```

### Step 1: Discover Agreement Keys

File:

```txt
discover_assist_keys.py
```

This script calls the ASSIST published agreements endpoint and saves agreement keys into the database.

Run:

```bash
python discover_assist_keys.py
```

This fills the `assist_agreement_keys` table.

The key format looks like:

```txt
76/113/to/79/Major/...
```

Meaning roughly:

| Part | Meaning |
|---|---|
| `76` | Academic year ID, currently 2025–2026 |
| `113` | De Anza College |
| `79` | UC Berkeley |
| `Major` | Agreement type |

Example campus configuration:

```python
RECEIVING_INSTITUTIONS = [
    {"id": 79, "name": "UC Berkeley"},
    {"id": 89, "name": "UC Davis"},
    {"id": 120, "name": "UC Irvine"},
]
```

### Step 2: Scrape Full ASSIST Agreements

File:

```txt
assist_scraper.py
```

This script reads unscraped keys from `assist_agreement_keys`, fetches the full agreement JSON from ASSIST, and saves it into `assist_agreements`.

Run:

```bash
python assist_scraper.py
```

The scraper usually fetches a batch at a time. If many keys are still unscraped, run it multiple times until all keys are scraped.

Check remaining keys by running:

```bash
python check_counts.py
```

or by checking the `scraped` column in the database.

### Step 3: Parse Raw ASSIST JSON

File:

```txt
parse_assist.py
```

This script reads raw JSON from `assist_agreements`, parses the articulation data, and saves clean searchable rows into `articulation_courses`.

Run:

```bash
python parse_assist.py
```

You do **not** need to scrape again if raw JSON is already saved. You can update the parser and rerun `parse_assist.py`.

---

## Full Data Update Workflow

When updating the database from ASSIST, run:

```bash
python discover_assist_keys.py
python assist_scraper.py
python parse_assist.py
python validate_data.py
```

If there are still unscraped keys, run:

```bash
python assist_scraper.py
```

again until all keys are scraped. Then rerun:

```bash
python parse_assist.py
python validate_data.py
```

---

## Running the Backend Server

For normal backend development:

```bash
python app.py
```

The backend runs at:

```txt
http://127.0.0.1:5000
```

For the actual website, you only need:

```bash
python app.py
```

You do **not** need to run the scraper or parser every time the website starts. The scraper and parser are only for updating the database.

---

## Running the Frontend with the Backend

Open one terminal:

```bash
cd backend
python app.py
```

Open another terminal:

```bash
cd frontend
npm run dev
```

The frontend usually runs at:

```txt
http://localhost:5173
```

The frontend sends requests to the Flask backend.

---

## Searching the Database from Python

File:

```txt
query_courses.py
```

This file provides the main search function used by the backend and AI model.

Example:

```python
from query_courses import search_articulations

rows = search_articulations(
    to_school="Berkeley",
    major="Aerospace",
    receiving="Reading",
    limit=10
)

for row in rows:
    print(row)
```

Parameters:

| Parameter | Meaning |
|---|---|
| `to_school` | UC campus name |
| `major` | Major name |
| `receiving` | UC-side course, course series, requirement, or breadth area |
| `cc_course` | De Anza course |
| `limit` | Maximum number of rows returned |

Example:

```python
search_articulations(
    to_school="Berkeley",
    major="Aerospace",
    receiving="Reading"
)
```

Meaning:

```txt
Find De Anza courses that satisfy Berkeley Aerospace Reading requirements.
```

Another example:

```python
search_articulations(
    cc_course="CIS 22C"
)
```

Meaning:

```txt
Find UC requirements that De Anza CIS 22C articulates to.
```

---

## Understanding Receiving vs Sending Side

ASSIST has two sides:

| Side | Meaning |
|---|---|
| Receiving side | UC side / target university requirement |
| Sending side | Community college side / De Anza course |

Example:

```txt
Receiving side:
UC Berkeley MATH 54 - Linear Algebra and Differential Equations

Sending side:
De Anza MATH 2A AND MATH 2B
```

In the database:

```txt
receiving_courses_text = UC-side course, series, requirement, or GE area
cc_prefix / cc_course_number / cc_course_title = De Anza course
```

---

## Receiving Types

ASSIST data is not always a simple one-to-one course mapping. The parser supports several receiving-side types.

### `Course`

A single UC course.

Example:

```txt
MATH 54 - Linear Algebra and Differential Equations
```

### `Series`

Multiple UC courses connected by `AND`.

Example:

```txt
I&C SCI 31 AND I&C SCI 32 AND I&C SCI 33
```

### `GeneralEducation`

A UC breadth or GE area.

Examples:

```txt
BS - BS-Biological Science
PS - PS-Physical Science
IS - IS-International Studies
```

### `Requirement`

A non-course requirement area.

Examples:

```txt
Courses that satisfy Reading & Composition A
Courses that satisfy Reading & Composition B
```

---

## Course Group Logic

The parser preserves ASSIST `AND` / `OR` logic using:

- `group_position`
- `course_position`
- `group_conjunction`
- `course_conjunction`

Example:

```txt
MATH 54
  Option 1:
    MATH 2A
    AND MATH 2B
  OR
  Option 2:
    MATH 2AH
    AND MATH 2BH
```

This is stored as:

```txt
group_conjunction = Or
course_conjunction = And
```

This is important because the chatbot should **not** say:

```txt
Take MATH 2A or MATH 2B.
```

when the correct meaning is:

```txt
Take MATH 2A and MATH 2B.
```

---

## Requirement Categories

The parser has a conservative `requirement_category` field.

Possible values:

| Category | Meaning |
|---|---|
| `required_for_admission` | Clearly required for admission or transfer admission |
| `major_requirements` | Lower-division major requirement or major requirement |
| `prerequisites_for_major` | Major preparation or prerequisite section |
| `strongly_recommended` | Clearly marked as strongly recommended |
| `highly_recommended` | Clearly marked as highly recommended |
| `recommended_not_required` | Recommended but explicitly not required |
| `recommended` | Recommended, but not enough context for a stronger label |
| `breadth_requirement` | General education, breadth, reading/composition, or similar requirement |
| `unknown` | The parser could not confidently classify the row |

> `unknown` does **not** mean bad data. It means the parser could not confidently classify the section as required, recommended, breadth, etc.

The chatbot should treat `unknown` cautiously and avoid saying a course is required unless the category clearly supports that.

---

## Requirement Instructions

The `requirement_instruction` field stores explicit or clearly generated structural instructions.

Examples:

```txt
Complete 1 series from the following
Choose one option from the following
Complete all listed groups
```

The parser intentionally avoids blindly generating:

```txt
Complete the following
```

ASSIST wording is inconsistent, and using that phrase incorrectly could mislead students.

---

## Notes

The `notes` field stores course-level or section-level notes.

Examples:

```txt
Regular and honors courses may be combined to complete this series
Effective next fall, this course will no longer articulate
Course is articulated in more than one agreement but credit can only apply to one
```

Notes should be shown to users when relevant because they can affect how an articulation should be interpreted.

---

## Validating the Database

File:

```txt
validate_data.py
```

Run:

```bash
python validate_data.py
```

This prints a summary like:

```txt
Rows with missing receiving side: 0
Rows with missing CC course: 0
Rows with unknown year: 0
Rows without explicit requirement instruction: ...

Rows by receiving_type:
Rows by requirement_category:
Agreements by UC campus:
```

The most important goals are:

```txt
Rows with missing receiving side: 0
Rows with missing CC course: 0
Rows with unknown year: 0
```

It is okay for many rows to have:

```txt
requirement_category = unknown
```

because the parser is conservative.

---

## Testing Queries

File:

```txt
test_query.py
```

Example:

```python
from query_courses import search_articulations

rows = search_articulations(
    to_school="Berkeley",
    major="Aerospace",
    receiving="Reading",
    limit=10
)

print("Number of rows:", len(rows))

for row in rows:
    print(row)
```

Run:

```bash
python test_query.py
```

Use this to test whether a specific school, major, receiving requirement, or De Anza course can be found.

---

## Checking Human-Readable Course Output

File:

```txt
check_courses.py
```

This prints parsed articulation rows in a more readable format. Use it to spot-check whether `AND` / `OR` grouping looks correct.

Run:

```bash
python check_courses.py
```

---

## Debug Scripts

Debug scripts are stored in:

```txt
debug_scripts/
```

These are not needed for normal backend operation. They are used only when inspecting raw ASSIST structures.

Examples:

```txt
inspect_assist.py
inspect_blank_uc.py
inspect_missing_receiving_side.py
inspect_requirement_type.py
verify_complete_following_source.py
```

If a debug script is moved into `debug_scripts/`, it may need this at the top to import files from the parent backend folder:

```python
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
```

Then it can import:

```python
from database import get_connection
```

---

## Important Development Notes

### Do Not Delete `raw_json`

The `raw_json` field in `assist_agreements` is important. It allows us to improve the parser and re-parse data later without scraping ASSIST again.

### Do Not Overclassify Requirement Categories

If a row is unclear, keep:

```txt
requirement_category = unknown
```

This is safer than incorrectly telling a student that a course is required or recommended.

### Do Not Run Scraper/Parser Every Time

For the website, only run:

```bash
python app.py
```

The scraper and parser are only needed when updating data.

### Be Careful with ASSIST Wording

ASSIST is inconsistent. Some agreements say:

```txt
Complete A, B, C, D, E, and F
```

Others say:

```txt
Complete 1 course from the following
```

Others use headings like:

```txt
Highly Recommended (but not required)
```

The parser should preserve useful structure and avoid making assumptions when the category is unclear.

---

## Recommended Workflow for New Developers

### First-Time Backend Setup

Windows:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install flask flask-cors requests
```

Mac/Linux:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install flask flask-cors requests
```

### Run Backend

```bash
python app.py
```

### Update ASSIST Data

```bash
python discover_assist_keys.py
python assist_scraper.py
python parse_assist.py
python validate_data.py
```

### Test Search

```bash
python test_query.py
```

### Start Frontend

```bash
cd ../frontend
npm install
npm run dev
```

---

## Current Backend Status

The backend currently supports:

- Flask API
- SQLite database
- ASSIST agreement key discovery
- ASSIST raw agreement scraping
- Parsing `Course`, `Series`, `GeneralEducation`, and `Requirement` receiving types
- `AND` / `OR` course grouping
- Notes
- Academic year metadata
- Search API for parsed articulation data
- Chat endpoint placeholder for AI integration

Next major work:

- Connect the AI model to `query_courses.py`
- Use parsed articulation results as context for chatbot answers
- Improve category parsing only when needed
- Add more campuses or agreement types if required
