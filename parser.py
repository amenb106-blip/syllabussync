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


def _find_date(line, academic_start_year):
    for pattern, separator, date_format in DATE_FORMATS:
        match = pattern.search(line)
        if match:
            month, day = match.group(1), match.group(2)
            # Use a leap year while identifying the month, then apply the
            # selected academic-year rule to the event itself.
            try:
                month_number = datetime.strptime(
                    separator.join([month, day, "2000"]), date_format
                ).month
                event_year = academic_start_year + (1 if month_number <= 7 else 0)
                text = separator.join([month, day, str(event_year)])
                return datetime.strptime(text, date_format).date()
            except ValueError:
                return None
    return None


def parse_syllabus(text, academic_start_year):
    """Return one calendar event for each line containing a supported date."""
    events = []
    for line in text.splitlines():
        date = _find_date(line, academic_start_year)
        if date is None:
            continue
        events.append({"name": line.split(":")[0].strip(), "date": date})
    return events


if __name__ == "__main__":
    sample = """Welcome to Bio 101
Midterm: October 12
Quiz 1: Oct 20
Lab report due 11/3
Final Exam: December 15"""

    for event in parse_syllabus(sample, 2026):
        print(event)
