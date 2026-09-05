import io
from datetime import date, datetime
from html.parser import HTMLParser

import pytest
from icalendar import Calendar
from werkzeug.datastructures import MultiDict

from app import app


class InputParser(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.inputs = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == "input":
            self.inputs.append(dict(attrs))


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
    checkboxes = [
        field for field in InputParser(response.get_data(as_text=True)).inputs
        if field.get("name") == "include"
    ]
    assert [(field["value"], "checked" in field) for field in checkboxes] == [
        ("0", True), ("1", False)
    ]


def test_pdf_extracted_text_remains_reviewable(client, monkeypatch):
    monkeypatch.setattr(
        "app.read_pdf_text", lambda _file, **_kwargs: "Quiz: October 12\nOffice hours: October 14"
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

    assert b"give us anything to read" in response.data


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

    assert b"read that file. Make sure" in response.data


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

def test_download_matches_selection_when_categories_interleave(client):
    syllabus = "Assignment due: Oct 12\nRead ch 3: Oct 13\nQuiz: Oct 14\nHomework due: Oct 15"

    response = client.post(
        "/generate",
        data={"syllabus": syllabus, "academic_start_year": "2026"},
    )
    assert response.status_code == 200


    form = [
        (field["name"], field.get("value", ""))
        for field in InputParser(response.get_data(as_text=True)).inputs
        if "name" in field
        and "disabled" not in field
        and (field.get("type") != "checkbox" or "checked" in field)
    ]

    download = client.post("/download", data=MultiDict(form))
    assert download.status_code == 200

    calendar = Calendar.from_ical(download.data)
    summaries = {
        str(component["SUMMARY"])
        for component in calendar.walk()
        if component.name == "VEVENT"
    }

    assert summaries == {"Assignment", "Homework", "Quiz"}


def test_review_page_offers_an_editable_time_for_each_event(client):
    response = client.post(
        "/generate",
        data={
            "syllabus": "Lab 1 due: October 12 at 11:59 PM\nMidterm: October 14",
            "academic_start_year": "2026",
        },
    )

    assert response.status_code == 200
    times = [
        field for field in InputParser(response.get_data(as_text=True)).inputs
        if field.get("name") == "event_time"
    ]
    assert [field.get("value") for field in times] == ["23:59", ""]


def test_download_emits_a_timed_event_and_keeps_untimed_ones_all_day(client):
    response = client.post(
        "/download",
        data=MultiDict(
            [
                ("name", "Lab 1"), ("event_date", "2026-10-12"), ("event_time", "23:59"),
                ("include", "0"),
                ("name", "Midterm"), ("event_date", "2026-10-14"), ("event_time", ""),
                ("include", "1"),
            ]
        ),
    )

    assert response.status_code == 200
    body = response.data.decode()
    assert "DTSTART:20261012T235900" in body
    assert "DTSTART;VALUE=DATE:20261014" in body
    assert "TZID" not in body

    events = {
        str(component["SUMMARY"]): component.decoded("DTSTART")
        for component in Calendar.from_ical(response.data).walk("VEVENT")
    }
    assert events["Lab 1"] == datetime(2026, 10, 12, 23, 59)
    assert events["Midterm"] == date(2026, 10, 14)


def test_download_rejects_an_unreadable_time(client):
    response = client.post(
        "/download",
        data=MultiDict(
            [("name", "Lab 1"), ("event_date", "2026-10-12"), ("event_time", "half past nine"),
             ("include", "0")]
        ),
    )

    assert b"needs a valid time" in response.data


def test_download_rejects_a_time_list_that_does_not_match_the_events(client):
    response = client.post(
        "/download",
        data=MultiDict(
            [("name", "Lab 1"), ("event_date", "2026-10-12"), ("event_time", "23:59"),
             ("name", "Midterm"), ("event_date", "2026-10-14"), ("include", "0")]
        ),
    )

    assert b"could not be read" in response.data
