from datetime import date

from parser import parse_syllabus


def test_full_month_name():
    events = parse_syllabus("Midterm: October 12", 2026)
    assert len(events) == 1
    assert events[0]["date"] == date(2026, 10, 12)


def test_abbreviated_month():
    events = parse_syllabus("Midterm: Oct 12", 2026)
    assert len(events) == 1
    assert events[0]["date"] == date(2026, 10, 12)


def test_numeric_slash_date():
    events = parse_syllabus("Quiz: 10/5", 2026)
    assert len(events) == 1
    assert events[0]["date"] == date(2026, 10, 5)


def test_line_with_no_date_is_skipped():
    assert parse_syllabus("Welcome to Bio 101", 2026) == []


def test_name_is_taken_from_before_the_colon():
    events = parse_syllabus("Final Exam: December 15", 2026)
    assert events[0]["name"] == "Final Exam"


def test_several_lines_together():
    text = """Welcome to Bio 101
Midterm: October 12
Quiz 1: Oct 20
Lab report: 11/3"""

    events = parse_syllabus(text, 2026)
    assert len(events) == 3
    assert events[0]["name"] == "Midterm"
    assert events[1]["date"] == date(2026, 10, 20)
    assert events[2]["date"] == date(2026, 11, 3)


def test_impossible_date_is_skipped():
    assert parse_syllabus("Bad date: February 30", 2026) == []


def test_spring_dates_use_the_following_calendar_year():
    events = parse_syllabus("Final: May 10", 2026)
    assert events[0]["date"] == date(2027, 5, 10)


def test_august_dates_stay_in_the_academic_start_year():
    events = parse_syllabus("First class: August 25", 2026)
    assert events[0]["date"] == date(2026, 8, 25)
