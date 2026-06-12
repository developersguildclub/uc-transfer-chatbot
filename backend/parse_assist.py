import json
import re
from html import unescape

from database import get_connection, setup_database


def clean_html_text(text):
    # Text cleanup makes ASSIST html readable before storing rows.
    if not text:
        return ""

    text = str(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = " ".join(text.split())
    return text.strip()


# Template ids connect ASSIST layout cells to articulation rows.
def iter_template_cell_ids(asset):
    cell_ids = []

    def walk(obj):
        if isinstance(obj, dict):
            if obj.get("id"):
                # Only articulation cell types can become receiving rows.
                if obj.get("type") in {"Course", "Series", "Requirement", "GeneralEducation"}:
                    cell_ids.append(obj.get("id"))

            for value in obj.values():
                walk(value)

        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(asset)
    return cell_ids


# Requirement titles live apart from rows, so this rebuilds labels.
def build_template_cell_title_map(template_assets):
    if isinstance(template_assets, str):
        try:
            template_assets = json.loads(template_assets)
        except Exception:
            template_assets = []

    assets = sorted(template_assets, key=lambda a: (a.get("area", ""), a.get("position", 0)))

    cell_title_map = {}
    current_requirement_title = ""

    for asset in assets:
        asset_type = asset.get("type")
        area = asset.get("area", "")

        if area != "Requirements":
            continue

        if asset_type == "RequirementTitle":
            current_requirement_title = clean_html_text(asset.get("content", ""))
            continue

        if asset_type != "RequirementGroup":
            continue

        # Requirement groups inherit the latest visible title.
        group_title = current_requirement_title

        # Inner headers add names like reading composition requirement.
        current_section_header = ""

        sections = asset.get("sections", [])
        for sec in sections:
            if sec.get("type") == "SectionHeader":
                current_section_header = clean_html_text(sec.get("content", ""))
                continue

            titles = [t for t in [group_title, current_section_header] if t]
            combined_title = " | ".join(titles)

            for cell_id in iter_template_cell_ids(sec):
                if combined_title:
                    cell_title_map[cell_id] = combined_title

    return cell_title_map


def extract_requirement_instruction(section):
    # Requirement instructions come from receiving attributes when present.
    attributes = section.get("receivingAttributes", [])
    texts = []

    if isinstance(attributes, str):
        try:
            attributes = json.loads(attributes)
        except Exception:
            attributes = []
    ignored_values = {
        "courseAttributes",
        "attributes",
        "type",
        "course",
        "Course",
        "courseGroup",
        "CourseGroup",
    }

    for attr in attributes:
        if isinstance(attr, dict):
            for key in ["content", "description", "label"]:
                value = attr.get(key)
                if value:
                    texts.append(value)

        elif isinstance(attr, str):
            value = attr.strip()

            if value in ignored_values:
                continue

            # Keep completion text, not generic course metadata.
            if "complete" in value.lower():
                texts.append(value)

    return " | ".join(dict.fromkeys(texts))


def format_course(course):
    # Course formatting preserves code and title for prompt display.
    prefix = course.get("prefix", "")
    number = course.get("courseNumber", "")
    title = course.get("courseTitle", "")

    course_code = f"{prefix} {number}".strip()

    if title:
        return f"{course_code} - {title}".strip(" -")

    return course_code


def extract_receiving_side(articulation):
    # Receiving-side parsing keeps UC course, series, GE, and requirement rows.
    articulation_type = articulation.get("type", "")

    # Course rows store one UC course.
    if articulation_type == "Course":
        course = articulation.get("course", {})
        uc_prefix, uc_number, uc_title = extract_course_name(course)
        receiving_text = format_course(course)

        return {
            "receiving_type": "Course",
            "uc_prefix": uc_prefix,
            "uc_number": uc_number,
            "uc_title": uc_title,
            "receiving_courses_text": receiving_text,
        }

    # Series rows keep the UC course group readable.
    if articulation_type == "Series":
        series = articulation.get("series", {})
        conjunction = series.get("conjunction", "And")
        courses = series.get("courses", [])

        courses = sorted(courses, key=lambda c: c.get("position", 0))

        course_texts = [format_course(course) for course in courses]
        receiving_text = f" {conjunction.upper()} ".join(course_texts)

        series_name = series.get("name") or receiving_text

        return {
            "receiving_type": "Series",
            "uc_prefix": "",
            "uc_number": "",
            "uc_title": series_name,
            "receiving_courses_text": receiving_text,
        }
    # GE rows keep breadth area text as the receiving side.
    if articulation_type == "GeneralEducation":
        ge_area = articulation.get("generalEducationArea", {})

        code = str(ge_area.get("code", "")).strip()
        name = str(ge_area.get("name", "")).strip()

        if code and name:
            receiving_text = f"{code} - {name}"
        elif name:
            receiving_text = name
        elif code:
            receiving_text = code
        else:
            receiving_text = "General Education Requirement"

        return {
            "receiving_type": "GeneralEducation",
            "uc_prefix": "",
            "uc_number": "",
            "uc_title": receiving_text,
            "receiving_courses_text": receiving_text,
        }

    # Requirement rows keep named admission or section requirements.
    if articulation_type == "Requirement":
        possible_fields = [
            articulation.get("requirement"),
            articulation.get("requirementArea"),
            articulation.get("requirementCategory"),
            articulation.get("requirementGroup"),
            articulation.get("name"),
            articulation.get("title"),
            articulation.get("label"),
        ]

        receiving_text = ""

        for field in possible_fields:
            if isinstance(field, dict):
                code = str(field.get("code", "")).strip()
                name = str(field.get("name", "")).strip()
                title = str(field.get("title", "")).strip()
                label = str(field.get("label", "")).strip()

                if code and name:
                    receiving_text = f"{code} - {name}"
                    break
                elif name:
                    receiving_text = name
                    break
                elif title:
                    receiving_text = title
                    break
                elif label:
                    receiving_text = label
                    break

            elif isinstance(field, str) and field.strip():
                receiving_text = field.strip()
                break

        # Attribute fallback catches requirement wording missed above.
        if not receiving_text:
            attributes = articulation.get("receivingAttributes", [])

            if isinstance(attributes, str):
                try:
                    attributes = json.loads(attributes)
                except Exception:
                    attributes = []

            for attr in attributes:
                if isinstance(attr, dict):
                    for key in ["content", "description", "label", "name", "title"]:
                        value = attr.get(key)
                        if value and "courseAttributes" not in str(value):
                            receiving_text = str(value).strip()
                            break

                elif isinstance(attr, str):
                    value = attr.strip()
                    if value and value not in ["courseAttributes", "attributes", "type"]:
                        receiving_text = value
                        break

                if receiving_text:
                    break

        if not receiving_text:
            receiving_text = "Requirement"

        return {
            "receiving_type": "Requirement",
            "uc_prefix": "",
            "uc_number": "",
            "uc_title": receiving_text,
            "receiving_courses_text": receiving_text,
        }

    # Unsupported receiving types stay visible instead of disappearing.
    return {
        "receiving_type": articulation_type or "Unknown",
        "uc_prefix": "",
        "uc_number": "",
        "uc_title": "",
        "receiving_courses_text": "",
    }


def generate_requirement_instruction(group_conjunction, course_groups):
    # Generated instructions capture clear ASSIST AND/OR structure.
    if len(course_groups) > 1 and group_conjunction == "Or":
        return "Choose one option from the following"

    if len(course_groups) > 1 and group_conjunction == "And":
        return "Complete all listed groups"

    return ""


def extract_course_name(course):
    # Course name extraction keeps parser inserts easy to read.
    prefix = course.get("prefix", "")
    number = course.get("courseNumber", "")
    title = course.get("courseTitle", "")
    return prefix, number, title


def extract_notes(course):
    # Course notes preserve ASSIST attributes beside each row.
    attributes = course.get("attributes", [])
    notes = []

    if isinstance(attributes, str):
        try:
            attributes = json.loads(attributes)
        except Exception:
            return attributes

    for attr in attributes:
        if isinstance(attr, dict):
            content = attr.get("content")
            if content:
                notes.append(content)
        elif isinstance(attr, str):
            notes.append(attr)

    return " | ".join(notes)


def extract_section_title(section, articulation):
    # Section titles name the ASSIST requirement around a row.
    possible_values = [
        section.get("title"),
        section.get("name"),
        section.get("label"),
        articulation.get("title"),
        articulation.get("name"),
        articulation.get("label"),
    ]

    # Requirement objects often carry the clearest section name.
    requirement = articulation.get("requirement")
    if isinstance(requirement, dict):
        possible_values.extend(
            [
                requirement.get("title"),
                requirement.get("name"),
                requirement.get("label"),
                requirement.get("description"),
            ]
        )

    # GE rows may expose code and name separately.
    ge_area = articulation.get("generalEducationArea")
    if isinstance(ge_area, dict):
        code = str(ge_area.get("code", "")).strip()
        name = str(ge_area.get("name", "")).strip()

        if code and name:
            possible_values.append(f"{code} - {name}")
        elif name:
            possible_values.append(name)
        elif code:
            possible_values.append(code)

    # Receiving attributes can contain section wording.
    receiving_attributes = articulation.get("receivingAttributes", [])

    if isinstance(receiving_attributes, str):
        try:
            receiving_attributes = json.loads(receiving_attributes)
        except Exception:
            receiving_attributes = []

    for attr in receiving_attributes:
        if isinstance(attr, dict):
            possible_values.extend(
                [
                    attr.get("content"),
                    attr.get("description"),
                    attr.get("label"),
                    attr.get("name"),
                    attr.get("title"),
                ]
            )
        elif isinstance(attr, str):
            possible_values.append(attr)

    ignored = {
        "courseAttributes",
        "attributes",
        "type",
        "Course",
        "Series",
        "GeneralEducation",
        "Requirement",
    }

    for value in possible_values:
        if not value:
            continue

        value = str(value).strip()

        if not value:
            continue

        if value in ignored:
            continue

        return value

    return ""


def has_any(text, phrases):
    return any(phrase in text for phrase in phrases)


def infer_requirement_category(
    section_title="", requirement_instruction="", notes="", receiving_type=""
):
    # Requirement category stays conservative for chatbot claim boundaries.
    combined_text = " ".join(
        [
            section_title or "",
            requirement_instruction or "",
            notes or "",
        ]
    ).lower()

    combined_text = " ".join(combined_text.split())

    # Not-required language wins before required-language checks.
    not_required_patterns = [
        r"not required",
        r"but not required",
        r"not required prior to transfer",
        r"recommended \(but not required\)",
        r"recommended, but not required",
    ]

    has_not_required = any(re.search(pattern, combined_text) for pattern in not_required_patterns)

    if has_not_required and "recommended" in combined_text:
        return "recommended_not_required"

    if "strongly recommended" in combined_text:
        return "strongly_recommended"

    if "highly recommended" in combined_text:
        return "highly_recommended"

    # Admission phrases become required-for-admission rows.
    required_for_admission_phrases = [
        "required for admission",
        "required courses for admission",
        "requirements for admission",
        "admission requirements",
        "required for transfer admission",
        "required prior to transfer",
        "required lower division courses",
    ]

    if has_any(combined_text, required_for_admission_phrases):
        return "required_for_admission"

    # Major-prep phrases become prerequisite rows.
    prerequisite_phrases = [
        "prerequisites for the major",
        "prerequisite courses",
        "major prerequisites",
        "preparation for the major",
        "major preparation",
        "courses required for preparation",
        "preparation courses for the major",
        "lower division prerequisites",
    ]

    if has_any(combined_text, prerequisite_phrases):
        return "prerequisites_for_major"

    # Major requirement phrases become major rows.
    major_requirement_phrases = [
        "major requirements",
        "lower division major requirements",
        "lower-division major requirements",
        "major required courses",
        "requirements for the major",
        "courses required for the major",
        "lower division requirements",
    ]

    if has_any(combined_text, major_requirement_phrases):
        return "major_requirements"

    # Breadth and GE phrases become breadth rows.
    breadth_phrases = [
        "breadth requirements",
        "breadth requirement",
        "breadth course",
        "general education",
        "ge requirement",
        "igetc",
        "reading and composition",
        "reading & composition",
        "american history and institutions",
    ]

    if has_any(combined_text, breadth_phrases):
        return "breadth_requirement"

    if receiving_type == "GeneralEducation":
        return "breadth_requirement"

    if "recommended" in combined_text:
        return "recommended"

    return "unknown"


def parse_and_save_courses():
    # Parser rebuilds searchable articulation rows from raw ASSIST JSON.
    setup_database()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, raw_json
        FROM assist_agreements
    """)

    rows = cursor.fetchall()

    if not rows:
        print("No ASSIST agreements found.")
        conn.close()
        return

    total_saved = 0

    for agreement_id, raw_json in rows:
        cursor.execute(
            """
            DELETE FROM articulation_courses
            WHERE agreement_id = ?
        """,
            (agreement_id,),
        )

        seen_courses = set()

        data = json.loads(raw_json)
        result = data.get("result", {})

        articulations_raw = result.get("articulations", "[]")
        template_assets_raw = result.get("templateAssets", "[]")
        template_cell_title_map = build_template_cell_title_map(template_assets_raw)

        try:
            articulations = json.loads(articulations_raw)
        except Exception as e:
            print(f"Could not parse articulations for agreement ID {agreement_id}")
            print("Error:", e)
            continue

        for section in articulations:
            articulation = section.get("articulation", {})

            template_cell_id = section.get("templateCellId", "")

            section_title = template_cell_title_map.get(template_cell_id) or extract_section_title(
                section, articulation
            )

            receiving_side = extract_receiving_side(articulation)
            receiving_type = receiving_side["receiving_type"]
            uc_prefix = receiving_side["uc_prefix"]
            uc_number = receiving_side["uc_number"]
            uc_title = receiving_side["uc_title"]
            receiving_courses_text = receiving_side["receiving_courses_text"]

            sending = articulation.get("sendingArticulation", {})
            course_groups = sending.get("items", [])

            group_conjunction = "Unknown"
            group_conjunctions = sending.get("courseGroupConjunctions", [])

            if group_conjunctions:
                group_conjunction = group_conjunctions[0].get("groupConjunction", "Unknown")

            requirement_instruction = extract_requirement_instruction(section)

            if not requirement_instruction:
                requirement_instruction = generate_requirement_instruction(
                    group_conjunction, course_groups
                )

            for group in course_groups:
                group_position = group.get("position", 0)
                course_conjunction = group.get("courseConjunction", "Unknown")
                cc_courses = group.get("items", [])

                for cc_course in cc_courses:
                    course_position = cc_course.get("position", 0)

                    cc_prefix, cc_number, cc_title = extract_course_name(cc_course)
                    notes = extract_notes(cc_course)
                    requirement_category = infer_requirement_category(
                        section_title=section_title,
                        requirement_instruction=requirement_instruction,
                        notes=notes,
                        receiving_type=receiving_type,
                    )

                    course_key = (
                        agreement_id,
                        receiving_type,
                        receiving_courses_text,
                        cc_prefix,
                        cc_number,
                        group_position,
                        course_position,
                    )

                    if course_key in seen_courses:
                        continue

                    seen_courses.add(course_key)

                    cursor.execute(
                        """
                        INSERT INTO articulation_courses (
                            agreement_id,
                            uc_prefix,
                            uc_course_number,
                            uc_course_title,
                            cc_prefix,
                            cc_course_number,
                            cc_course_title,
                            group_position,
                            course_position,
                            group_conjunction,
                            course_conjunction,
                            requirement_instruction,
                            requirement_category,
                            section_title,
                            notes,
                            receiving_type,
                            receiving_courses_text
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            agreement_id,
                            uc_prefix,
                            uc_number,
                            uc_title,
                            cc_prefix,
                            cc_number,
                            cc_title,
                            group_position,
                            course_position,
                            group_conjunction,
                            course_conjunction,
                            requirement_instruction,
                            requirement_category,
                            section_title,
                            notes,
                            receiving_type,
                            receiving_courses_text,
                        ),
                    )

                    total_saved += 1

    conn.commit()
    conn.close()

    print("Done parsing all agreements.")
    print(f"Saved {total_saved} articulated course rows.")


if __name__ == "__main__":
    parse_and_save_courses()
