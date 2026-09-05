from datetime import date

import pytest

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

    assert [event["name"] for event in events] == [
        "No class", "Guest lecture", "Thanksgiving holiday"
    ]
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


@pytest.mark.parametrize(
    "date_text, expected",
    [
        ("May 10, 2026", date(2026, 5, 10)),
        ("October 12 2027", date(2027, 10, 12)),
        ("Oct. 12, 2025", date(2025, 10, 12)),
        ("Oct 12 2027", date(2027, 10, 12)),
        ("5/10/2026", date(2026, 5, 10)),
        ("10/12/2025", date(2025, 10, 12)),
        ("February 29, 2024", date(2024, 2, 29)),
        ("2/29/2024", date(2024, 2, 29)),
    ],
)
def test_explicit_year_overrides_academic_year(date_text, expected):
    events = parse_syllabus(f"{date_text} - Final Exam", 2026)

    assert len(events) == 1
    assert events[0]["date"] == expected
    assert events[0]["name"] == "Final Exam"


@pytest.mark.parametrize("date_text", ["February 29, 2025", "2/29/2025", "May 10, 0000"])
def test_invalid_explicit_dates_do_not_fall_back_to_academic_year(date_text):
    assert parse_syllabus(f"Final Exam: {date_text}", 2023) == []


@pytest.mark.parametrize("prefix", ["If", "For example,", "Suppose", "For example:\n"])
def test_policy_examples_are_left_unselected(prefix):
    events = parse_syllabus(f"{prefix} an assignment is due September 3", 2025)

    assert len(events) == 1
    assert events[0]["default_selected"] is False
    assert events[0]["category"] == "Policy and administration"


def test_exam_heading_applies_to_sections_but_does_not_leak_to_other_events():
    events = parse_syllabus(
        "Midterm\nSection 001: October 9, 2025 in class\n"
        "Section 002: October 10, 2025 in class\n"
        "Reading schedule\nRead Chapter 2: October 11", 2025
    )

    assert len(events) == 3
    assert all(event["name"].startswith("Midterm: Section") for event in events[:2])
    assert all(event["default_selected"] for event in events[:2])
    assert events[2]["name"] == "Read Chapter 2"
    assert events[2]["default_selected"] is False


def test_exam_heading_gives_a_bare_date_a_name():
    events = parse_syllabus("Midterm\nOctober 9, 2025", 2026)

    assert len(events) == 1
    assert events[0]["name"] == "Midterm"
    assert events[0]["date"] == date(2025, 10, 9)


@pytest.mark.parametrize(
    "window, closing_date",
    [
        ("between 4:00PM October 12, 2025 and\n3:59PM October 13, 2025", date(2025, 10, 13)),
        ("from 11:50AM December 17, 2025 --\n11:49AM December 18, 2025", date(2025, 12, 18)),
        ("from 5/10/2026 to May 11", date(2026, 5, 11)),
        ("from December 30, 2025 through January 2", date(2026, 1, 2)),
    ],
)
def test_exam_window_exports_one_closing_day_with_range_in_name(window, closing_date):
    events = parse_syllabus(f"Final exam {window}", 2025)

    assert len(events) == 1
    assert events[0]["date"] == closing_date
    assert events[0]["name"].startswith("Final exam (exam window:")
    assert closing_date.isoformat() in events[0]["name"]
    assert "closing day" in events[0]["reason"]


def test_separate_exam_dates_are_not_combined_into_a_window():
    events = parse_syllabus("Midterm: October 8\nFinal exam: December 17", 2025)

    assert [(event["name"], event["date"]) for event in events] == [
        ("Midterm", date(2025, 10, 8)), ("Final exam", date(2025, 12, 17))
    ]


def test_window_continuation_does_not_absorb_an_unrelated_deadline():
    events = parse_syllabus(
        "Online exam available from October 8 and\nHomework due October 10", 2025
    )

    assert len(events) == 2
    assert events[0]["date"] == date(2025, 10, 8)
    assert events[1]["name"] == "Homework"
    assert events[1]["date"] == date(2025, 10, 10)


def test_final_project_is_a_deadline_and_exact_duplicate_events_are_removed():
    events = parse_syllabus(
        "Final Term Project submission: December 4\n"
        "Final Term Project submission: December 4", 2025
    )

    assert len(events) == 1
    assert events[0]["category"] == "Deadlines"
