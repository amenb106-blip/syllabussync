
import re
from datetime import datetime


FULL_MONTH = re.compile(
    r"\b(January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+(\d{1,2})\b(?:,?\s+(\d{4})\b)?",
    re.IGNORECASE,
)
ABBREV_MONTH = re.compile(
    r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+(\d{1,2})\b"
    r"(?:,?\s+(\d{4})\b)?",
    re.IGNORECASE,
)
NUMERIC = re.compile(r"\b(\d{1,2})/(\d{1,2})\b(?:/(\d{4})\b)?(?!/\d)")

DATE_FORMATS = [
    (FULL_MONTH, " ", "%B %d %Y"),
    (ABBREV_MONTH, " ", "%b %d %Y"),
    (NUMERIC, "/", "%m/%d/%Y"),
]

SELECTED_RULES = [
    (
        "Assessments",
        re.compile(
            r"\b(?:quiz|exam|midterm|test|final(?!\s+(?:term\s+)?(?:project|report|presentation|paper)))\b",
            re.IGNORECASE,
        ),
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
EXAM_HEADING = re.compile(r"^(?:midterm|final(?:\s+exam)?|exam|quiz)(?:\s+\d+)?\s*:?$", re.IGNORECASE)
POLICY_EXAMPLE = re.compile(r"^(?:if\b|for example\b|e\.g\.|suppose\b|assuming\b)", re.IGNORECASE)
WINDOW_START = re.compile(r"\b(?:between|from)\b", re.IGNORECASE)
WINDOW_CONNECTOR = re.compile(r"^\s*(?:and|to|until|through|--?|\u2013|\u2014)\s*", re.IGNORECASE)
TIME_PREFIX = re.compile(r"^\s*(?:\d{1,2}(?::\d{2})?\s*(?:AM|PM)?\s*)?$", re.IGNORECASE)


def _find_date(line, academic_start_year):
    matches = [
        (match, separator, date_format)
        for pattern, separator, date_format in DATE_FORMATS
        if (match := pattern.search(line)) is not None
    ]
    for match, separator, date_format in sorted(matches, key=lambda item: item[0].start()):
        month, day, explicit_year = match.groups()
        try:
            if explicit_year is not None:
                event_year = int(explicit_year)
            else:
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
    if POLICY_EXAMPLE.search(line):
        return (
            "Policy and administration", "low", False,
            "Conditional or example date; check whether this is an actual deadline.",
        )
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


def _event_lines(text, academic_start_year):
    lines = [" ".join(line.split()) for line in text.splitlines()]
    heading = None
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        if not line:
            continue
        if EXAM_HEADING.fullmatch(line):
            heading = line.rstrip(":")
            continue
        if line.lower() in {"for example:", "for example", "suppose:"} and index < len(lines):
            line += " " + lines[index]
            index += 1
        parsed_date, date_match = _find_date(line, academic_start_year)
        if parsed_date is not None:
            if WINDOW_START.search(line) and re.search(r"(?:and|to|until|through|--?|\u2013|\u2014)$", line, re.IGNORECASE):
                if index < len(lines):
                    next_date, next_match = _find_date(lines[index], academic_start_year)
                    if next_date is not None and TIME_PREFIX.fullmatch(lines[index][:next_match.start()]):
                        line += " " + lines[index]
                        index += 1
            date_match = _find_date(line, academic_start_year)[1]
            if heading and (
                re.match(r"^Section\s+\S+:", line, re.IGNORECASE)
                or _event_name(line, date_match) is None
            ):
                line = f"{heading}: {line}"
            else:
                heading = None
            yield line
        else:
            heading = None


def parse_syllabus(text, academic_start_year):
    events = []
    seen = set()
    for line in _event_lines(text, academic_start_year):
        date, date_match = _find_date(line, academic_start_year)
        if date is None:
            continue

        name = _event_name(line, date_match)
        if name is None:
            continue

        category, confidence, default_selected, reason = _classify(line)
        remaining = line[date_match.end():]
        if category == "Assessments" and WINDOW_START.search(line[:date_match.start()]):
            connector = WINDOW_CONNECTOR.match(remaining)
            if connector:
                window_end = remaining[connector.end():]
                end_date, end_match = _find_date(window_end, academic_start_year)
                if end_date is not None and TIME_PREFIX.fullmatch(window_end[:end_match.start()]):
                    if end_match.group(3) is None:
                        try:
                            end_date = end_date.replace(year=date.year + (end_date.month < date.month))
                        except ValueError:
                            end_date = None
                    if end_date is not None and end_date >= date:
                        section = re.search(r"\bSection\s+[^:]+", line, re.IGNORECASE)
                        label = line.split(":", 1)[0] if section else line[:WINDOW_START.search(line).start()].rstrip(" :-")
                        if section and section.group() != label:
                            label += " - " + section.group()
                        name = f"{label} (exam window: {date.isoformat()} to {end_date.isoformat()})"
                        date = end_date
                        reason = "Exam window; calendar marks the closing day. Check the syllabus for exact times."
        identity = (name.casefold(), date)
        if identity in seen:
            continue
        seen.add(identity)
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
