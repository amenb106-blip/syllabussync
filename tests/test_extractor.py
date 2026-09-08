from datetime import date, time

import extractor
from extractor import extract_events, _to_event


def test_extract_events_returns_ai_result(monkeypatch):
    fake = [
        {
            "name": "From AI",
            "date": date(2026, 10, 12),
            "time": None,
            "category": "Assessments",
            "confidence": "high",
            "default_selected": True,
            "reason": "Assessment identified by the AI.",
        }
    ]
    monkeypatch.setattr(extractor, "_extract_with_ai", lambda text, year: fake)

    assert extract_events("anything", 2026) == fake


def test_to_event_maps_selected_category():
    event = _to_event(
        {"name": "Essay 1 due", "date": "2026-09-25", "time": "23:59", "category": "Deadlines"}
    )

    assert event["date"] == date(2026, 9, 25)
    assert event["time"] == time(23, 59)
    assert event["default_selected"] is True
    assert event["confidence"] == "high"


def test_to_event_defaults_unknown_category_and_stays_unselected():
    event = _to_event({"name": "Course founded", "date": "2026-10-12", "category": "nonsense"})

    assert event["category"] == "Other dated text"
    assert event["default_selected"] is False
    assert event["time"] is None


def test_to_event_strips_pdf_artifacts_from_name():
    event = _to_event(
        {"name": "(cid:127) Midterm  Exam", "date": "2026-10-20", "category": "Assessments"}
    )

    assert event["name"] == "Midterm Exam"


def test_to_event_rejects_missing_name_or_date():
    assert _to_event({"date": "2026-10-12", "category": "Deadlines"}) is None
    assert _to_event({"name": "No date", "category": "Deadlines"}) is None
    assert _to_event({"name": "Bad date", "date": "not-a-date"}) is None
