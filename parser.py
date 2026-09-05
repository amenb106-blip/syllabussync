
import re
from datetime import datetime


FULL_MONTH = re.compile(
    r"\b(January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+(\d{1,2})\b",
    re.IGNORECASE,
)
ABBREV_MONTH = re.compile(
    r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+(\d{1,2})\b",
    re.IGNORECASE,
)
NUMERIC = re.compile(r"\b(\d{1,2})/(\d{1,2})\b")

DATE_FORMATS = [
    (FULL_MONTH, " ", "%B %d %Y"),
    (ABBREV_MONTH, " ", "%b %d %Y"),
    (NUMERIC, "/", "%m/%d/%Y"),
]

# These rules deliberately describe syllabus language rather than trying to
# guess from the date alone. That keeps the parser predictable and testable.
SELECTED_RULES = [
    (
        "Assessments",
        re.compile(r"\b(?:quiz|exam|midterm|final|test)\b", re.IGNORECASE),
        "high",
        "Assessment keyword found.",
    ),
    (
        "Deadlines",
        re.compile(
            r"\b(?:assignment|homework|hw|project|paper|essay|report|lab|"
            r"presentation|proposal|discussion|due|submit|submission)\b",
            re.IGNORECASE,
        ),
        "high",
        "Deadline keyword found.",
    ),
    (
        "Schedule changes",
        re.compile(
            r"\b(?:holiday|no class|cancel(?:led|ed)?|make[- ]?up|"
            r"special session|guest lecture|field trip|review session)\b",
            re.IGNORECASE,
        ),
        "high",
        "One-time schedule-change keyword found.",
    ),
]

UNSELECTED_RULES = [
    (
        "Readings",
        re.compile(r"\b(?:reading|read|chapter|pages?|textbook)\b", re.IGNORECASE),
        "low",
        "Reading-related date; left for the student to choose.",
    ),
    (
        "Office hours",
        re.compile(r"\boffice hours?\b", re.IGNORECASE),
        "low",
        "Office-hours date; left for the student to choose.",
    ),
    (
        "Policy and administration",
        re.compile(
            r"\b(?:syllabus|withdraw(?:al)?|registration|tuition|add/drop|"
            r"drop deadline|policy|census)\b",
            re.IGNORECASE,
        ),
        "low",
        "Administrative date; left for the student to choose.",
    ),
    (
        "Routine course dates",
        re.compile(
            r"\b(?:first class|last class|class meets|course begins|course ends|"
            r"semester begins|semester ends)\b",
            re.IGNORECASE,
        ),
        "low",
        "Routine course date; left for the student to choose.",
    ),
]

GENERIC_NAME = re.compile(
    r"^(?:(?:week|module|unit)\s*\d+|date|tbd|schedule|calendar)$", re.IGNORECASE
)
TRAILING_CONNECTOR = re.compile(r"\b(?:by|due|on)\s*[-:\u2013\u2014]*\s*$", re.IGNORECASE)


def _find_date(line, academic_start_year):
    for pattern, separator, date_format in DATE_FORMATS:
        match = pattern.search(line)
        if not match:
            continue

        month, day = match.group(1), match.group(2)
        try:
            # Use a leap year while identifying the month, then apply the
            # selected academic-year rule to the event itself.
            month_number = datetime.strptime(
                separator.join([month, day, "2000"]), date_format
            ).month
            event_year = academic_start_year + (1 if month_number <= 7 else 0)
            date_text = separator.join([month, day, str(event_year)])
            return datetime.strptime(date_text, date_format).date(), match
        except ValueError:
            return None, None
    return None, None


def _event_name(line, date_match):
    without_date = f"{line[:date_match.start()]} {line[date_match.end():]}"
    name = re.sub(r"\s+", " ", without_date).strip(" \t:-\u2013\u2014|()[]")
    name = TRAILING_CONNECTOR.sub("", name).strip(" \t:-\u2013\u2014|()[]")

    if not name or GENERIC_NAME.fullmatch(name):
        return None
    return name


def _classify(line):
    for category, pattern, confidence, reason in SELECTED_RULES:
        if pattern.search(line):
            return category, confidence, True, reason

    for category, pattern, confidence, reason in UNSELECTED_RULES:
        if pattern.search(line):
            return category, confidence, False, reason

    return (
        "Other dated text",
        "low",
        False,
        "A date was found, but no event or schedule-change keyword was found.",
    )


def parse_syllabus(text, academic_start_year):
    events = []
    for line in text.splitlines():
        date, date_match = _find_date(line, academic_start_year)
        if date is None:
            continue

        name = _event_name(line, date_match)
        if name is None:
            continue

        category, confidence, default_selected, reason = _classify(line)
        events.append(
            {
                "name": name,
                "date": date,
                "category": category,
                "confidence": confidence,
                "default_selected": default_selected,
                "reason": reason,
            }
        )
    return events
