import json
import re
from datetime import date, time

import config

_ARTIFACTS = re.compile(r"\(cid:\d+\)|�")

_SELECTED = {"Assessments", "Deadlines", "Schedule changes"}

_CATEGORY_REASON = {
    "Assessments": "Assessment identified by the AI.",
    "Deadlines": "Deadline identified by the AI.",
    "Schedule changes": "One-time schedule change identified by the AI.",
    "Readings": "Reading-related date; left for you to choose.",
    "Office hours": "Office-hours date; left for you to choose.",
    "Policy and administration": "Administrative date; left for you to choose.",
    "Routine course dates": "Routine course date; left for you to choose.",
    "Other dated text": "The AI found a date but no clear event type.",
}
_DEFAULT_CATEGORY = "Other dated text"


def extract_events(text, academic_start_year):
    return _extract_with_ai(text, academic_start_year)


def _extract_with_ai(text, academic_start_year):
    from google import genai

    client = genai.Client(api_key=config.api_key())
    cleaned = _ARTIFACTS.sub(" ", text)[: config.max_input_chars()]
    response = client.models.generate_content(
        model=config.model(),
        contents=_build_prompt(cleaned, academic_start_year),
        config={"response_mime_type": "application/json"},
    )
    items = json.loads(response.text)
    return [event for event in (_to_event(item) for item in items) if event]


def _to_event(item):
    if not isinstance(item, dict):
        return None
    name = _ARTIFACTS.sub(" ", item.get("name") or "")
    name = " ".join(name.split())
    if not name:
        return None
    try:
        event_date = date.fromisoformat(item["date"])
    except (KeyError, TypeError, ValueError):
        return None

    event_time = None
    raw_time = item.get("time")
    if raw_time:
        try:
            event_time = time.fromisoformat(raw_time)
        except (TypeError, ValueError):
            event_time = None

    category = item.get("category")
    if category not in _CATEGORY_REASON:
        category = _DEFAULT_CATEGORY

    return {
        "name": name,
        "date": event_date,
        "time": event_time,
        "category": category,
        "confidence": "high" if category in _SELECTED else "low",
        "default_selected": category in _SELECTED,
        "reason": _CATEGORY_REASON[category],
    }


def _build_prompt(text, academic_start_year):
    categories = ", ".join(f'"{name}"' for name in _CATEGORY_REASON)
    return (
        "You extract calendar events from a college course syllabus.\n\n"
        "Return ONLY a JSON array. Each element is an object with keys:\n"
        '- "name": a short title of 3 to 6 words naming the assessment or '
        "deliverable only. Do not include grade weights, percentages, room "
        "locations, descriptions, parentheses, or scheduling words such as "
        '"All Day", "Class Hours", or "End of Day". '
        'Examples: "Midterm Exam", "Quiz 1 due", "Final Project due".\n'
        '- "date": the date as ISO "YYYY-MM-DD".\n'
        '- "time": 24-hour "HH:MM" if the syllabus states one, otherwise null.\n'
        f'- "category": exactly one of: {categories}.\n\n'
        f"Year rule: the academic year starts in {academic_start_year}. "
        f"Dates in August-December use {academic_start_year}; dates in "
        f"January-July use {academic_start_year + 1}. If the syllabus writes a "
        "full year, use that instead.\n\n"
        "If the same event appears more than once on the same date, include it "
        "only once. Include only real dated items. If there are none, return [].\n\n"
        "Syllabus:\n"
        f"{text}\n"
    )
