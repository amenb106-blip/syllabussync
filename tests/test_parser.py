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


@pytest.mark.parametrize("summary_first", [False, True])
def test_repeated_exam_summary_is_unchecked_but_kept_for_review(summary_first):
    section = "Midterm\nSection 001: October 8, 2025 in class"
    summary = "Course topic Midterm: October 8, 2025"
    text = f"{summary}\n{section}" if summary_first else f"{section}\n{summary}"
    events = parse_syllabus(text, 2025)

    assert len(events) == 2
    assert sum(event["default_selected"] for event in events) == 1
    assert next(event for event in events if "Section 001" in event["name"])["default_selected"]
    repeated = next(event for event in events if event["name"] == "Course topic Midterm")
    assert repeated["confidence"] == "low"
    assert "Possible repeated listing" in repeated["reason"]


def test_duplicate_detection_preserves_distinct_sections_exam_numbers_and_review_sessions():
    events = parse_syllabus(
        "Midterm\nSection 001: October 8\nSection 002: October 8\n"
        "Exam 1: October 8\nExam 2: October 8\nMidterm review: October 8", 2025
    )

    assert len(events) == 5
    assert all(event["default_selected"] for event in events)


def test_duplicate_detection_preserves_different_named_courses():
    events = parse_syllabus("Biology midterm: October 8\nChemistry midterm: October 8", 2025)

    assert len(events) == 2
    assert all(event["default_selected"] for event in events)


@pytest.mark.parametrize(
    "line, expected",
    [
        ("Final exam: May 10,2026", date(2026, 5, 10)),
        ("Final exam: May 10,  2026", date(2026, 5, 10)),
        ("Final exam: October 12th", date(2026, 10, 12)),
        ("Final exam: Oct 3rd", date(2026, 10, 3)),
        ("Final exam: Oct. 21st, 2027", date(2027, 10, 21)),
        ("Final exam: Sept 16", date(2026, 9, 16)),
        ("Final exam: Sept. 16, 2027", date(2027, 9, 16)),
        ("Final exam: 10/12/25", date(2025, 10, 12)),
        ("Final exam: 6-10-26", date(2026, 6, 10)),
        ("Final exam: 6-10-2026", date(2026, 6, 10)),
    ],
)
def test_tight_years_ordinals_and_short_year_formats(line, expected):
    events = parse_syllabus(line, 2026)

    assert [event["date"] for event in events] == [expected]
    assert events[0]["name"] == "Final exam"


@pytest.mark.parametrize(
    "line",
    [
        "Read the policy at https://policies.ncsu.edu/regulation/reg-02-20-01/",
        "Attendance regulation reg-02-20-03-attendance-regulations applies",
        "Grading policy pol-11-35-01 covers academic integrity",
    ],
)
def test_hyphenated_policy_numbers_are_not_read_as_dates(line):
    assert parse_syllabus(line, 2025) == []


def test_leap_day_window_resolves_against_the_opening_year():
    events = parse_syllabus("Final exam from February 28, 2024 through February 29", 2024)

    assert len(events) == 1
    assert events[0]["date"] == date(2024, 2, 29)
    assert "2024-02-28 to 2024-02-29" in events[0]["name"]


def test_leap_day_window_spanning_two_lines_is_joined():
    events = parse_syllabus(
        "Final exam between February 28, 2024 and\nFebruary 29", 2024
    )

    assert len(events) == 1
    assert events[0]["date"] == date(2024, 2, 29)


def test_different_courses_keep_their_own_exams_on_a_shared_date():
    events = parse_syllabus(
        "Midterm\nSection 001: October 8\nPHYS 201 Midterm: October 8", 2025
    )

    assert len(events) == 2
    assert all(event["default_selected"] for event in events)


def test_course_codes_in_parentheses_are_preserved_and_kept_distinct():
    events = parse_syllabus(
        "Exam 1 (BIO 101): October 8\nExam 1 (CHEM 110): October 8", 2025
    )

    assert [event["name"] for event in events] == ["Exam 1 (BIO 101)", "Exam 1 (CHEM 110)"]
    assert all(event["default_selected"] for event in events)


def test_empty_brackets_left_by_a_removed_date_are_dropped():
    events = parse_syllabus("Term Project Proposal submission (11/4)", 2025)

    assert [event["name"] for event in events] == ["Term Project Proposal submission"]


def test_summer_session_keeps_july_and_august_in_the_same_year():
    events = parse_syllabus(
        "Quiz 1: June 8\nQuiz 2: July 6\nQuiz 3: July 27\nFinal exam: August 7", 2025
    )

    assert [event["date"] for event in events] == [
        date(2026, 6, 8), date(2026, 7, 6), date(2026, 7, 27), date(2026, 8, 7)
    ]


def test_fall_to_spring_schedule_still_rolls_over_at_the_new_year():
    events = parse_syllabus(
        "Quiz 1: September 8\nMidterm: December 10\nQuiz 2: January 20\nFinal exam: May 5",
        2025,
    )

    assert [event["date"] for event in events] == [
        date(2025, 9, 8), date(2025, 12, 10), date(2026, 1, 20), date(2026, 5, 5)
    ]


def test_undated_events_follow_the_years_stated_elsewhere_in_the_syllabus():
    events = parse_syllabus(
        "Course runs September 9, 2026 to December 16, 2026\n"
        "Lab 1 due: September 16\nFinal exam: December 14",
        2025,
    )

    assert [event["date"] for event in events[-2:]] == [date(2026, 9, 16), date(2026, 12, 14)]


@pytest.mark.parametrize(
    "line, expected_time, expected_name",
    [
        ("Lab 1 Due: Sept 16 at 11:59 PM", "23:59", "Lab 1"),
        ("Final Code Submission: Dec 16 at 5:00 PM", "17:00", "Final Code Submission"),
        ("Quiz 1 due July 10 at 11:59 P.M.", "23:59", "Quiz 1"),
        ("Third Exam October 8 will be held at 5:30P.M.", "17:30", "Third Exam will be held"),
        ("Homework due 1/12 9:00am", "09:00", "Homework"),
        ("Office hours on Zoom 1/12 6:00-7:00 pm", "18:00", "Office hours on Zoom"),
        ("Office hours on Zoom 1/12 6:00 - 7:00 pm", "18:00", "Office hours on Zoom"),
        ("Class 1/12 9 to 10:30am", "09:00", "Class"),
        ("Final exam October 8 12:00-2:30PM", "12:00", "Final exam"),
        ("Final exam October 8 11:50AM -- 1:50PM", "11:50", "Final exam"),
        ("Orientation 1/12 12:00 AM", "00:00", "Orientation"),
        ("Lunch talk 1/12 12:00 PM", "12:00", "Lunch talk"),
    ],
)
def test_start_times_are_extracted_and_removed_from_the_name(line, expected_time, expected_name):
    events = parse_syllabus(line, 2025)

    assert len(events) == 1
    assert events[0]["time"].isoformat("minutes") == expected_time
    assert events[0]["name"] == expected_name


@pytest.mark.parametrize(
    "line",
    [
        "Read Chapter 4: October 12",
        "Midterm Examination: October 12",
        "Project Proposal due October 30",
    ],
)
def test_events_without_a_time_stay_all_day(line):
    events = parse_syllabus(line, 2025)

    assert len(events) == 1
    assert events[0]["time"] is None


def test_a_time_in_the_middle_of_a_name_is_left_in_place():
    events = parse_syllabus(
        "Midterm: October 8 Section 001: 11:50AM -- 1:50PM, Education Room #7", 2025
    )

    assert events[0]["time"].isoformat("minutes") == "11:50"
    assert events[0]["name"] == "Midterm: Section 001: 11:50AM -- 1:50PM, Education Room #7"


@pytest.mark.parametrize(
    "line, expected",
    [
        (
            "First Exam (Chapters 1-4) will be held on October 8, worth 55 points.",
            "First Exam (Chapters 1-4) will be held, worth 55 points.",
        ),
        (
            "Chapter 17 PowerPoint presentations due in class on August 6.",
            "Chapter 17 PowerPoint presentations due in class.",
        ),
        (
            "Week 1 January 9 ( , 1/11) Reading Assignment: Ch 1.1",
            "Week 1 (1/11) Reading Assignment: Ch 1.1",
        ),
    ],
)
def test_debris_from_a_removed_mid_sentence_date_is_cleaned_up(line, expected):
    assert [event["name"] for event in parse_syllabus(line, 2025)] == [expected]


@pytest.mark.parametrize(
    "line, expected",
    [
        ("Opens 1/2 Module 0 Class introduction", "Opens Module 0 Class introduction"),
        ("Week 06 Oct 12, 2026 Midterm Examination", "Week 06 Midterm Examination"),
    ],
)
def test_cleanup_does_not_swallow_the_subject_of_the_event(line, expected):
    assert [event["name"] for event in parse_syllabus(line, 2025)] == [expected]


@pytest.mark.parametrize(
    "line, expected_time, expected_name",
    [
        ("9/1/26 10:00am-11:30am First day of class: intro topology",
         "10:00", "First day of class: intro topology"),
        ("Sept 8 Due by 11:59pm Quiz 1 Online Portal Deadline",
         "23:59", "Quiz 1 Online Portal Deadline"),
        ("9/16 5 PM sharp Lab 2: Protocol Analysis submission", "17:00", "Lab 2: Protocol Analysis submission"),
        ("9/22/26 @ 11:59 PM Term project proposal draft", "23:59", "Term project proposal draft"),
        ("10/27 11:59 PM Quiz 3 Deadline: transport layers", "23:59", "Quiz 3 Deadline: transport layers"),
        ("Dec 15 10:00 AM - 12:00 PM Comprehensive Final Examination",
         "10:00", "Comprehensive Final Examination"),
        ("11/10/26 Midnight Milestone 2 Verification Check-in", "00:00", "Milestone 2 Verification Check-in"),
        ("11/10/26 Noon Milestone 3 Verification Check-in", "12:00", "Milestone 3 Verification Check-in"),
    ],
)
def test_a_time_column_before_the_event_name_is_read_and_removed(line, expected_time, expected_name):
    events = parse_syllabus(line, 2026)

    assert len(events) == 1
    assert events[0]["time"].isoformat("minutes") == expected_time
    assert events[0]["name"] == expected_name


def test_a_date_range_keeps_the_opening_day_and_drops_the_closing_one_from_the_name():
    events = parse_syllabus("Nov 3 - Nov 5 All Day Reading Framework: Chapters 7.1 to 7.3", 2026)

    assert len(events) == 1
    assert events[0]["date"] == date(2026, 11, 3)
    assert events[0]["name"] == "All Day Reading Framework: Chapters 7.1 to 7.3"


@pytest.mark.parametrize(
    "line, expected",
    [
        (
            "Midterm Exam: 25% of grade. Scheduled explicitly on October 20 during the class block.",
            "Midterm Exam: 25% of grade. Scheduled explicitly during the class block.",
        ),
        (
            "Term Project: final deliverables must be committed by 12/3 before 11:59PM.",
            "Term Project: final deliverables must be committed",
        ),
    ],
)
def test_two_prepositions_left_touching_by_a_removed_date_are_collapsed(line, expected):
    assert [event["name"] for event in parse_syllabus(line, 2026)] == [expected]


@pytest.mark.parametrize(
    "line, expected",
    [
        ("Chapter 17 presentations due in class on August 6.", "Chapter 17 presentations due in class."),
        ("Final Term Project Submission due at the start of class 10/22",
         "Final Term Project Submission due at the start of class"),
        ("Lecture 5 Nonexperimental Methods on August 3", "Lecture 5 Nonexperimental Methods"),
    ],
)
def test_cleanup_leaves_ordinary_phrasing_alone(line, expected):
    assert [event["name"] for event in parse_syllabus(line, 2026)] == [expected]
