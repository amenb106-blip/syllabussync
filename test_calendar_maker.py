from datetime import date

from icalendar import Calendar

from calendar_maker import make_calendar


def test_make_calendar_creates_events_with_names_and_dates():
    calendar_data = make_calendar(
        [
            {"name": "Midterm", "date": date(2026, 10, 12)},
            {"name": "Final", "date": date(2027, 3, 15)},
        ]
    )

    calendar = Calendar.from_ical(calendar_data)
    events = [component for component in calendar.walk() if component.name == "VEVENT"]

    assert [str(event["SUMMARY"]) for event in events] == ["Midterm", "Final"]
    assert events[0].decoded("DTSTART") == date(2026, 10, 12)
    assert events[1].decoded("DTSTART") == date(2027, 3, 15)
