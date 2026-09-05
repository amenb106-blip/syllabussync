import re

from pypdf import PdfReader


def read_pdf_text(uploaded_file):
    reader = PdfReader(uploaded_file)
    lines = []
    columns = None
    cells = None

    def flush():
        nonlocal cells
        if cells is not None:
            lines.extend(" ".join(parts) for parts in cells[1:] if parts)
            cells = None

    for page in reader.pages:
        text = page.extract_text(extraction_mode="layout", layout_mode_space_vertically=False) or ""
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
