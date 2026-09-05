import re
from io import BytesIO

import pdfplumber
from pypdf import PdfReader

from parser import DATE_PATTERNS

TOPIC_HEADING = re.compile(
    r"\b(?:topic|event|description|lecture|subject|activit)", re.IGNORECASE
)
DEADLINE_HEADING = re.compile(
    r"\b(?:assignment|homework|hw|due|deliverable|deadline|assessment|lab|project|exam|quiz)",
    re.IGNORECASE,
)


def _cell_dates(text):
    return {
        (match.start(), match.end())
        for pattern in DATE_PATTERNS
        for match in pattern.finditer(text)
    }


def _dated_table_lines(table):
    rows = table.extract()
    if not rows or not (rows[0][0] or "").strip().casefold().startswith("date"):
        return None
    headings = [(cell or "").strip() for cell in rows[0]]
    topic_index = next(
        (i for i, heading in enumerate(headings[1:], start=1) if TOPIC_HEADING.search(heading)),
        None,
    )
    if topic_index is None:
        return None
    deadline_indexes = [
        i
        for i, heading in enumerate(headings[1:], start=1)
        if i != topic_index and DEADLINE_HEADING.search(heading)
    ]

    lines = []
    for row in rows[1:]:
        cells = [" ".join((cell or "").split()) for cell in row]
        matches = _cell_dates(cells[0])
        if not matches:
            if any(cells):
                return None
            continue
        if len(matches) != 1:
            return None
        start, end = next(iter(matches))
        date_text = cells[0][start:end]
        if cells[topic_index]:
            lines.append(f"{date_text} - {cells[topic_index]}")
        for index in deadline_indexes:
            for part in cells[index].split(";"):
                part = part.strip()
                if part:
                    lines.append(part if _cell_dates(part) else f"{date_text} - {part}")
    return lines or None


def _replace_dated_tables(page):
    tables = [
        (table.bbox, lines)
        for table in page.find_tables()
        if (lines := _dated_table_lines(table)) is not None
    ]
    if not tables:
        return None

    def outside_tables(obj):
        if "x0" not in obj or "top" not in obj:
            return True
        x = (obj["x0"] + obj["x1"]) / 2
        y = (obj["top"] + obj["bottom"]) / 2
        return not any(left <= x <= right and top <= y <= bottom for (left, top, right, bottom), _ in tables)

    blocks = [
        (line["top"], line["text"])
        for line in page.filter(outside_tables).extract_text_lines()
    ]
    blocks.extend((bbox[1], "\n".join(lines)) for bbox, lines in tables)
    return "\n".join(text for _, text in sorted(blocks, key=lambda block: block[0]))


def _looks_scanned(page, text):
    page_area = page.width * page.height
    covering = any(
        (image["x1"] - image["x0"]) * (image["bottom"] - image["top"]) >= 0.6 * page_area
        for image in page.images
    )
    return covering and len("".join(text.split())) < 200


def read_pdf_text(uploaded_file, *, skipped_pages=None):
    data = uploaded_file.read()
    reader = PdfReader(BytesIO(data))
    pages = []
    with pdfplumber.open(BytesIO(data)) as document:
        for index, page in enumerate(reader.pages, start=1):
            table_page = document.pages[index - 1] if index <= len(document.pages) else None
            text = (
                page.extract_text(extraction_mode="layout", layout_mode_space_vertically=False) or ""
                if "/Contents" in page else ""
            )
            if table_page is not None and skipped_pages is not None and _looks_scanned(table_page, text):
                skipped_pages.append(index)
            if text.strip() and table_page is not None:
                table_text = _replace_dated_tables(table_page)
                if table_text is not None:
                    text = table_text
            pages.append(text)
    return _join_weekly_cells(pages)


def _join_weekly_cells(pages):
    lines = []
    columns = None
    cells = None

    def flush():
        nonlocal cells
        if cells is not None:
            lines.extend(" ".join(parts) for parts in cells[1:] if parts)
            cells = None

    for text in pages:
        for line in text.splitlines():
            if re.match(r"^\s*Week\s{2,}", line, re.IGNORECASE):
                flush()
                columns = [match.start() for match in re.finditer(r"\S.*?(?=\s{2,}|$)", line)]
                if len(columns) < 2:
                    columns = None
                continue

            if columns is not None and line.strip():
                first = line[:columns[1]].strip()
                if not first or re.fullmatch(r"\d{1,2}|Finals?|week", first, re.IGNORECASE):
                    if first and first.lower() != "week":
                        flush()
                        cells = [[] for _ in columns]
                    if cells is not None:
                        for index, start in enumerate(columns):
                            end = columns[index + 1] if index + 1 < len(columns) else None
                            value = " ".join(line[start:end].split())
                            if value:
                                cells[index].append(value)
                        continue
                flush()
                columns = None

            lines.append(" ".join(line.split()))
        flush()

    return "\n".join(lines)
