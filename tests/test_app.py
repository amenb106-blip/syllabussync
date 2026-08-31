import io

import pytest
from icalendar import Calendar
from werkzeug.datastructures import MultiDict

from app import app


@pytest.fixture()
def client():
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client


def test_home_shows_academic_year_input(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"academic_start_year" in response.data


def test_generate_shows_review_page_and_rolls_spring_dates_forward(client):
    response = client.post(
        "/generate",
        data={
            "syllabus": "Midterm: October 12\nFinal: May 10",
            "academic_start_year": "2026",
        },
    )

    assert response.status_code == 200
    assert b"Review your events" in response.data
    assert b"2026-10-12" in response.data
    assert b"2027-05-10" in response.data


def test_generate_groups_candidates_and_only_selects_actionable_events(client):
    response = client.post(
        "/generate",
        data={
            "syllabus": "Assignment due: October 12\nRead Chapter 3: October 14",
            "academic_start_year": "2026",
        },
    )

    assert response.status_code == 200
    assert b"Deadlines" in response.data
    assert b"Readings" in response.data
    assert b"Deadline keyword found." in response.data
    assert response.data.count(b'name="include"') == 2
    assert response.data.count(b'name="include" value="0"\n                                           checked') == 1


def test_pdf_extracted_text_remains_reviewable(client, monkeypatch):
    monkeypatch.setattr(
        "app.read_pdf_text", lambda _file: "Quiz: October 12\nOffice hours: October 14"
    )

    response = client.post(
        "/generate",
        data={
            "academic_start_year": "2026",
            "pdf": (io.BytesIO(b"placeholder"), "syllabus.pdf"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert b"Assessments" in response.data
    assert b"Office hours" in response.data


def test_generate_rejects_empty_syllabus(client):
    response = client.post("/generate", data={"syllabus": "", "academic_start_year": "2026"})

    assert b"didn't give us anything" in response.data


def test_generate_rejects_invalid_academic_year(client):
    response = client.post(
        "/generate", data={"syllabus": "Quiz: October 12", "academic_start_year": "nope"}
    )

    assert b"valid academic start year" in response.data


def test_generate_rejects_an_unreadable_pdf(client):
    response = client.post(
        "/generate",
        data={
            "academic_start_year": "2026",
            "pdf": (io.BytesIO(b"not a PDF"), "syllabus.pdf"),
        },
        content_type="multipart/form-data",
    )

    assert b"couldn't read that file" in response.data


def test_download_uses_edited_events_and_ignores_unchecked_ones(client):
    response = client.post(
        "/download",
        data=MultiDict(
            [
                ("name", "Updated Midterm"),
                ("event_date", "2026-10-15"),
                ("include", "0"),
                ("name", "Ignore me"),
                ("event_date", "2026-10-16"),
            ]
        ),
    )

    assert response.status_code == 200
    assert response.mimetype == "text/calendar"
    calendar = Calendar.from_ical(response.data)
    events = [component for component in calendar.walk() if component.name == "VEVENT"]
    assert len(events) == 1
    assert str(events[0]["SUMMARY"]) == "Updated Midterm"
    assert events[0].decoded("DTSTART").isoformat() == "2026-10-15"
