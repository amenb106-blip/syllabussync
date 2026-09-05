
import re
from datetime import date, time


MONTHS = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sept": 9, "sep": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

ORDINAL_DAY = r"(\d{1,2})(?:st|nd|rd|th)?\b"
TRAILING_YEAR = r"(?:,?\s*(\d{4})\b)?"

FULL_MONTH = re.compile(
    r"\b(January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+" + ORDINAL_DAY + TRAILING_YEAR,
    re.IGNORECASE,
)
ABBREV_MONTH = re.compile(
    r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec)\.?\s+"
    + ORDINAL_DAY + TRAILING_YEAR,
    re.IGNORECASE,
)
NUMERIC = re.compile(r"\b(\d{1,2})/(\d{1,2})\b(?:/(\d{2,4})\b)?(?!/\d)")
DASHED = re.compile(r"(?<![-\w])(\d{1,2})-(\d{1,2})-(\d{2,4})(?![-\w])")

DATE_PATTERNS = [FULL_MONTH, ABBREV_MONTH, NUMERIC, DASHED]
DEFAULT_BOUNDARY = 8
MAX_TERM_DAYS = 305

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
ASSESSMENT_LABEL = re.compile(
    r"\b(midterm(?:\s+exam)?|final(?:\s+exam)?|exam|quiz|test)(?:\s*#?\s*(\d+|[IVX]+))?\b",
    re.IGNORECASE,
)
ASSESSMENT_PREPARATION = re.compile(r"\b(?:review|practice|preparation|worksheet|study|retake|make[- ]?up)\b", re.IGNORECASE)
SECTION = re.compile(r"\bSection\s+([\w/-]+)", re.IGNORECASE)
COURSE_CODE = re.compile(r"\b([A-Z]{2,5})\s?-?\s?(\d{3,4}[A-Z]?)\b")
EDGE_CHARACTERS = " \t:,-–—|"
EMPTY_BRACKETS = re.compile(r"\s*[(\[]\s*[)\]]\s*")
BRACKET_COMMA = re.compile(r"([(\[])\s*,\s*")
DANGLING_CONNECTOR = re.compile(r"\b(?:by|due|on|from)\s*([,;.])", re.IGNORECASE)
SPACED_PUNCTUATION = re.compile(r"\s+([,.;])")

MERIDIEM = r"\s*([AaPp])\.?\s?[Mm]\.?"
TIME_OF_DAY = re.compile(r"\b(\d{1,2})(?::(\d{2}))?" + MERIDIEM)
TIME_RANGE_START = re.compile(
    r"\b(\d{1,2})(?::(\d{2}))?\s*(?:[-–—]|to)\s*\d{1,2}(?::\d{2})?" + MERIDIEM
)
NAMED_TIME = re.compile(r"\b(midnight|noon)\b", re.IGNORECASE)
NAMED_TIMES = {"midnight": time(0, 0), "noon": time(12, 0)}

CLOCK = r"\d{1,2}(?::\d{2})?\s*[AaPp]\.?\s?[Mm]\.?"
TIME_LEAD = r"(?:due\s+)?(?:@|\bat\b|\bby\b|\bfrom\b|\bbefore\b|\buntil\b)?\s*"
TIME_BODY = (
    r"(?:(?:\d{1,2}(?::\d{2})?(?:\s*[AaPp]\.?\s?[Mm]\.?)?\s*(?:[-–—]{1,2}|to)\s*)?"
    + CLOCK + r"|\bmidnight\b|\bnoon\b)"
)
LEADING_TIME = re.compile(
    r"^[\s:]*" + TIME_LEAD + TIME_BODY + r"\s*(?:sharp\b)?[\s:,–—-]*", re.IGNORECASE
)
TRAILING_TIME = re.compile(
    r"[\s:]*" + TIME_LEAD + TIME_BODY + r"\s*\.?\s*$", re.IGNORECASE
)
RANGE_TO_DATE = re.compile(r"^\s*(?:[-–—]{1,2}|to|through|until)\s+", re.IGNORECASE)
DOUBLE_CONNECTOR = re.compile(
    r"\b(?:by|due|on|from)\s+(?=(?:during|before|after)\b)", re.IGNORECASE
)


def _date_parts(text):
    matches = [
        match for pattern in DATE_PATTERNS if (match := pattern.search(text)) is not None
    ]
    if not matches:
        return None
    match = min(matches, key=lambda item: item.start())
    month_text, day_text, year_text = match.groups()
    month = int(month_text) if month_text.isdigit() else MONTHS[month_text.casefold()]
    if year_text is None:
        year = None
    else:
        year = int(year_text) + 2000 * (len(year_text) == 2)
    return month, int(day_text), year, match


def _build_date(month, day, year):
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _find_date(line, academic_start_year, boundary=DEFAULT_BOUNDARY):
    parts = _date_parts(line)
    if parts is None:
        return None, None
    month, day, explicit_year, match = parts
    year = explicit_year if explicit_year is not None else academic_start_year + (month < boundary)
    event_date = _build_date(month, day, year)
    return (event_date, match) if event_date is not None else (None, None)


def _year_boundary(text, academic_start_year):
    parsed = [
        parts[:3]
        for line in text.splitlines()
        if (parts := _date_parts(line)) is not None
    ]
    if len(parsed) < 2 or all(year is not None for _, _, year in parsed):
        return DEFAULT_BOUNDARY

    best = None
    for boundary in range(1, 14):
        dates = [
            found
            for month, day, year in parsed
            if (found := _build_date(
                month, day, academic_start_year + (month < boundary) if year is None else year
            ))
        ]
        if len(dates) < 2:
            continue
        span = (max(dates) - min(dates)).days
        score = (
            span > MAX_TERM_DAYS,
            sum(later < earlier for earlier, later in zip(dates, dates[1:])),
            span,
            abs(boundary - DEFAULT_BOUNDARY),
        )
        if best is None or score < best[0]:
            best = (score, boundary)
    return best[1] if best else DEFAULT_BOUNDARY


def _build_time(match):
    hour, minute, meridiem = match.group(1, 2, 3)
    hour = int(hour)
    if not 1 <= hour <= 12:
        return None
    if meridiem.casefold() == "p":
        hour = hour % 12 + 12
    else:
        hour = hour % 12
    try:
        return time(hour, int(minute or 0))
    except ValueError:
        return None


def _find_time(line):
    single = TIME_OF_DAY.search(line)
    ranged = TIME_RANGE_START.search(line)
    if ranged is not None and (single is None or ranged.start() <= single.start()):
        return _build_time(ranged)
    if single is not None:
        return _build_time(single)
    named = NAMED_TIME.search(line)
    return NAMED_TIMES[named.group(1).casefold()] if named is not None else None


def _trim(name):
    name = EMPTY_BRACKETS.sub(" ", name).strip(EDGE_CHARACTERS)
    while name and (name[0] in ")]" or name[-1] in "(["):
        name = (name[1:] if name[0] in ")]" else name[:-1]).strip(EDGE_CHARACTERS)
    return name


def _event_name(line, date_match):
    after = line[date_match.end():]
    connector = RANGE_TO_DATE.match(after)
    if connector is not None:
        second = _date_parts(after[connector.end():])
        if second is not None and second[3].start() == 0:
            after = after[connector.end() + second[3].end():]

    name = re.sub(r"\s+", " ", f"{line[:date_match.start()]} {after}")
    name = SPACED_PUNCTUATION.sub(
        r"\1", DANGLING_CONNECTOR.sub(r"\1", BRACKET_COMMA.sub(r"\1", name))
    )
    name = _trim(LEADING_TIME.sub("", _trim(DOUBLE_CONNECTOR.sub("", name))))
    name = _trim(TRAILING_TIME.sub("", name))
    name = _trim(TRAILING_CONNECTOR.sub("", name))

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


def _event_lines(text, academic_start_year, boundary):
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
        parsed_date, date_match = _find_date(line, academic_start_year, boundary)
        if parsed_date is not None:
            if WINDOW_START.search(line) and re.search(r"(?:and|to|until|through|--?|\u2013|\u2014)$", line, re.IGNORECASE):
                if index < len(lines):
                    next_parts = _date_parts(lines[index])
                    if next_parts is not None and TIME_PREFIX.fullmatch(
                        lines[index][:next_parts[3].start()]
                    ):
                        line += " " + lines[index]
                        index += 1
            date_match = _find_date(line, academic_start_year, boundary)[1]
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


def _mark_repeated_assessments(events):
    groups = {}
    for event in events:
        match = ASSESSMENT_LABEL.search(event["name"])
        if event["category"] != "Assessments" or match is None or ASSESSMENT_PREPARATION.search(event["name"]):
            continue
        label = match.group(1).casefold().removesuffix(" exam")
        course = COURSE_CODE.search(event["name"])
        key = (
            event["date"],
            label,
            (match.group(2) or "").casefold(),
            course.group(1, 2) if course else None,
        )
        groups.setdefault(key, []).append(event)

    for group in groups.values():
        section_events = [event for event in group if SECTION.search(event["name"])]
        bare_events = [event for event in group if ASSESSMENT_LABEL.fullmatch(event["name"])]
        repeated = (
            [event for event in group if not SECTION.search(event["name"])]
            if section_events else bare_events[1:]
        )
        for event in repeated:
            event["default_selected"] = False
            event["confidence"] = "low"
            event["reason"] = (
                "Possible repeated listing: another entry names the same assessment on this date. "
                "Left unchecked; select it if it is a separate event."
            )


def parse_syllabus(text, academic_start_year):
    events = []
    seen = set()
    boundary = _year_boundary(text, academic_start_year)
    for line in _event_lines(text, academic_start_year, boundary):
        event_date, date_match = _find_date(line, academic_start_year, boundary)
        if event_date is None:
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
                end_parts = _date_parts(window_end)
                if end_parts is not None and TIME_PREFIX.fullmatch(
                    window_end[:end_parts[3].start()]
                ):
                    end_month, end_day, end_year, _ = end_parts
                    if end_year is None:
                        end_year = event_date.year + (end_month < event_date.month)
                    end_date = _build_date(end_month, end_day, end_year)
                    if end_date is not None and end_date >= event_date:
                        section = re.search(r"\bSection\s+[^:]+", line, re.IGNORECASE)
                        label = line.split(":", 1)[0] if section else line[:WINDOW_START.search(line).start()].rstrip(" :-")
                        if section and section.group() != label:
                            label += " - " + section.group()
                        name = f"{label} (exam window: {event_date.isoformat()} to {end_date.isoformat()})"
                        event_date = end_date
                        reason = "Exam window; calendar marks the closing day. Check the syllabus for exact times."
        identity = (name.casefold(), event_date)
        if identity in seen:
            continue
        seen.add(identity)
        events.append(
            {
                "name": name,
                "date": event_date,
                "time": _find_time(line),
                "category": category,
                "confidence": confidence,
                "default_selected": default_selected,
                "reason": reason,
            }
        )
    _mark_repeated_assessments(events)
    return events
