from datetime import date

from parser import parse_syllabus


def event_for(events, name):
    return next(event for event in events if event["name"] == name)


def test_full_month_name_and_assessment_metadata():
    events = parse_syllabus("Midterm: October 12", 2026)

    assert len(events) == 1
    assert events[0]["date"] == date(2026, 10, 12)
    assert events[0]["category"] == "Assessments"
    assert events[0]["default_selected"] is True


def test_abbreviated_month_and_numeric_dates_are_supported():
    events = parse_syllabus("Quiz: Oct 12\nLab report due 11/3", 2026)

    assert event_for(events, "Quiz")["date"] == date(2026, 10, 12)
    assert event_for(events, "Lab report")["date"] == date(2026, 11, 3)


def test_deadlines_and_assessments_are_selected_by_default():
    events = parse_syllabus(
        "Assignment 1 due: September 9\nFinal Exam: December 15\nPresentation: May 10",
        2026,
    )

    assert [event["default_selected"] for event in events] == [True, True, True]
    assert [event["category"] for event in events] == ["Deadlines", "Assessments", "Deadlines"]


def test_readings_office_hours_and_policy_dates_are_not_selected_by_default():
    events = parse_syllabus(
        "Read Chapter 4: October 12\nOffice hours begin: October 14\nDrop deadline: November 1",
        2026,
    )

    assert [event["default_selected"] for event in events] == [False, False, False]
    assert [event["category"] for event in events] == [
        "Readings",
        "Office hours",
        "Policy and administration",
    ]


def test_holidays_cancellations_and_special_sessions_are_selected():
    events = parse_syllabus(
        "No class: October 12\nGuest lecture: October 20\nThanksgiving holiday: November 27",
        2026,
    )

    assert all(event["default_selected"] for event in events)
    assert all(event["category"] == "Schedule changes" for event in events)


def test_generic_dated_text_is_available_but_not_selected():
    events = parse_syllabus("The university was founded on October 12", 2026)

    assert events[0]["category"] == "Other dated text"
    assert events[0]["default_selected"] is False
    assert events[0]["confidence"] == "low"


def test_empty_or_generic_names_are_skipped():
    assert parse_syllabus("October 12\nWeek 3: October 20", 2026) == []


def test_impossible_date_and_lines_without_dates_are_skipped():
    assert parse_syllabus("Bad date: February 30\nWelcome to Bio 101", 2026) == []


def test_spring_dates_use_the_following_calendar_year():
    events = parse_syllabus("Final: May 10", 2026)

    assert events[0]["date"] == date(2027, 5, 10)


def test_date_at_the_start_of_a_line_is_removed_from_the_event_name():
    events = parse_syllabus("October 12 - Midterm Exam", 2026)

    assert events[0]["name"] == "Midterm Exam"
