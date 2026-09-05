from datetime import date, datetime, timezone, timedelta

from icalendar import Calendar

from calendar_maker import make_calendar


def test_make_calendar_creates_events_with_names_and_dates():
    before = datetime.now(timezone.utc).replace(microsecond=0)
    calendar_data = make_calendar(
        [
            {"name": "Midterm", "date": date(2026, 10, 12)},
            {"name": "Final", "date": date(2027, 3, 15)},
        ]
    )

    calendar = Calendar.from_ical(calendar_data)
    after = datetime.now(timezone.utc)
    assert calendar["VERSION"] == "2.0"
    assert calendar["PRODID"]
    events = [component for component in calendar.walk() if component.name == "VEVENT"]

    assert [str(event["SUMMARY"]) for event in events] == ["Midterm", "Final"]
    assert events[0].decoded("DTSTART") == date(2026, 10, 12)
    assert events[1].decoded("DTSTART") == date(2027, 3, 15)
    for event in events:
        assert event["DTSTART"].params["VALUE"] == "DATE"
        assert before <= event.decoded("DTSTAMP") <= after
        assert event.decoded("DTSTAMP").utcoffset() == timedelta(0)
        assert event["UID"]


def test_event_ids_are_stable_across_exports_and_independent_of_selection_order():
    events = [
        {"name": "Midterm", "date": date(2026, 10, 12)},
        {"name": "Midterm", "date": date(2026, 10, 13)},
        {"name": "Final", "date": date(2026, 10, 12)},
    ]

    original = Calendar.from_ical(make_calendar(events)).walk("VEVENT")
    reordered = Calendar.from_ical(make_calendar(list(reversed(events)))).walk("VEVENT")
    selected = Calendar.from_ical(make_calendar(events[:1])).walk("VEVENT")

    original_ids = [str(event["UID"]) for event in original]
    assert len(set(original_ids)) == 3
    assert [str(event["UID"]) for event in reordered] == list(reversed(original_ids))
    assert str(selected[0]["UID"]) == original_ids[0]
