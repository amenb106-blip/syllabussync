import io
from datetime import date, datetime, time
from html.parser import HTMLParser

import pytest
from icalendar import Calendar
from werkzeug.datastructures import MultiDict

import app as app_module
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


def _event(name, event_date, category, default_selected, event_time=None):
    return {
        "name": name,
        "date": event_date,
        "time": event_time,
        "category": category,
        "confidence": "high" if default_selected else "low",
        "default_selected": default_selected,
        "reason": category + " event",
    }


def _use_events(monkeypatch, events):
    monkeypatch.setattr(app_module, "extract_events", lambda text, year: events)


def test_home_shows_academic_year_input(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"academic_start_year" in response.data


def test_generate_renders_extracted_events(client, monkeypatch):
    _use_events(monkeypatch, [
        _event("Midterm", date(2026, 10, 12), "Assessments", True),
        _event("Final", date(2027, 5, 10), "Assessments", True),
    ])

    response = client.post(
        "/generate",
        data={"syllabus": "whatever", "academic_start_year": "2026"},
    )

    assert response.status_code == 200
    assert b"Review your events" in response.data
    assert b"2026-10-12" in response.data
    assert b"2027-05-10" in response.data


def test_generate_groups_events_and_selects_only_actionable_ones(client, monkeypatch):
    _use_events(monkeypatch, [
        _event("Assignment", date(2026, 10, 12), "Deadlines", True),
        _event("Read Chapter 3", date(2026, 10, 14), "Readings", False),
    ])

    response = client.post(
        "/generate",
        data={"syllabus": "whatever", "academic_start_year": "2026"},
    )

    assert response.status_code == 200
    assert b"Deadlines" in response.data
    assert b"Readings" in response.data
    checkboxes = [
        field for field in InputParser(response.get_data(as_text=True)).inputs
        if field.get("name") == "include"
    ]
    assert [(field["value"], "checked" in field) for field in checkboxes] == [
        ("0", True), ("1", False)
    ]


def test_pdf_text_flows_into_review(client, monkeypatch):
    monkeypatch.setattr("app.read_pdf_text", lambda _file, **_kwargs: "extracted text")
    _use_events(monkeypatch, [
        _event("Quiz", date(2026, 10, 12), "Assessments", True),
        _event("Office hours", date(2026, 10, 14), "Office hours", False),
    ])

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

    assert b"Upload a PDF or paste syllabus text" in response.data


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


def test_download_matches_selection_when_categories_interleave(client, monkeypatch):
    _use_events(monkeypatch, [
        _event("Assignment", date(2026, 10, 12), "Deadlines", True),
        _event("Read ch 3", date(2026, 10, 13), "Readings", False),
        _event("Quiz", date(2026, 10, 14), "Assessments", True),
        _event("Homework", date(2026, 10, 15), "Deadlines", True),
    ])

    response = client.post(
        "/generate",
        data={"syllabus": "whatever", "academic_start_year": "2026"},
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


def test_review_page_offers_an_editable_time_for_each_event(client, monkeypatch):
    _use_events(monkeypatch, [
        _event("Lab 1", date(2026, 10, 12), "Deadlines", True, event_time=time(23, 59)),
        _event("Midterm", date(2026, 10, 14), "Assessments", True),
    ])

    response = client.post(
        "/generate",
        data={"syllabus": "whatever", "academic_start_year": "2026"},
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


def test_api_extract_serializes_dates_and_times(client, monkeypatch):
    captured = []
    def extract(text, year):
        captured.append((text, year))
        return [_event('Quiz', date(2027, 1, 2), 'Assessments', True, time(9, 30))]
    monkeypatch.setattr(app_module, 'extract_events', extract)
    response = client.post('/api/extract', data={'syllabus': 'Quiz Jan 2', 'academic_start_year': '2026'})
    assert response.status_code == 200
    assert captured == [('Quiz Jan 2', 2026)]
    assert response.json['events'][0]['date'] == '2027-01-02'
    assert response.json['events'][0]['time'] == '09:30'
    assert response.json['events'][0]['default_selected'] is True
    assert response.json['warnings'] == []


@pytest.mark.parametrize('data', [
    {'syllabus': '', 'academic_start_year': '2026'},
    {'syllabus': 'Quiz', 'academic_start_year': 'invalid'},
    {'syllabus': 'Quiz', 'academic_start_year': '2101'},
])
def test_api_invalid_input_is_json(client, data):
    response = client.post('/api/extract', data=data)
    assert response.status_code == 400
    assert response.json['error']['message']


def test_api_extraction_failure_does_not_leak_exception(client, monkeypatch):
    def fail(*args):
        raise RuntimeError('secret provider error')
    monkeypatch.setattr(app_module, 'extract_events', fail)
    response = client.post('/api/extract', data={'syllabus': 'Quiz', 'academic_start_year': '2026'})
    assert response.status_code == 502
    assert 'secret' not in response.get_data(as_text=True)
    assert response.json['error']['message'] == 'Unable to extract events. Try again shortly.'


def test_api_pdf_warning_and_empty_results(client, monkeypatch):
    def read(file, skipped_pages):
        skipped_pages.extend([2, 4])
        return 'syllabus'
    monkeypatch.setattr(app_module, 'read_pdf_text', read)
    _use_events(monkeypatch, [])
    response = client.post('/api/extract', data={
        'pdf': (io.BytesIO(b'pdf'), 'course.pdf'), 'academic_start_year': '2026',
    })
    assert response.status_code == 200
    assert response.json['events'] == []
    assert '2, 4' in response.json['warnings'][0]


def test_api_unreadable_pdf(client):
    response = client.post('/api/extract', data={
        'pdf': (io.BytesIO(b'bad file'), 'course.pdf'), 'academic_start_year': '2026',
    })
    assert response.status_code == 400
    assert response.json['error']['message']


@pytest.mark.parametrize('reminder', ['', '15', '60', '1440'])
def test_download_reminder(client, reminder):
    response = client.post('/download', data={
        'name': 'Final', 'event_date': '2026-12-12', 'include': '0', 'reminder_minutes': reminder,
    })
    assert response.status_code == 200
    alarms = Calendar.from_ical(response.data).walk('VALARM')
    assert len(alarms) == (1 if reminder else 0)
    if reminder:
        from datetime import timedelta
        assert alarms[0].decoded('TRIGGER') == -timedelta(minutes=int(reminder))
        assert alarms[0]['ACTION'] == 'DISPLAY'


@pytest.mark.parametrize('reminder', ['0', '-15', '30', 'abc'])
def test_download_rejects_invalid_reminders(client, reminder):
    response = client.post('/download', data={'reminder_minutes': reminder})
    assert response.status_code == 400
