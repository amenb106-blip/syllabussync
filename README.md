# SyllabusSync

Turn a course syllabus into a calendar file.

**Live app:** https://syllabussync-sand.vercel.app

Paste your syllabus text or upload the PDF. SyllabusSync finds the exams, assignments, and due dates, lets you review and edit them, then gives you an `.ics` file you can import into Google Calendar, Apple Calendar, or Outlook.

## How it works

1. **Add a syllabus** – paste the text or upload a PDF with selectable text, and choose the academic start year.
2. **Find dates** – the parser scans each line for dates like `October 12`, `Oct 12`, or `10/12` and uses the surrounding text as the event name.
3. **Review** – events are grouped (Assessments, Deadlines, Readings, etc.). Clear deadlines are pre-selected; you can fix names and dates or untick anything that doesn't belong.
4. **Download** – the selected events are written to a standard `.ics` file as all-day events.

Dates without a year use the chosen academic year: August–December use the start year and January–July roll forward to the next year. A four-digit year written in the syllabus takes priority, including formats such as `May 10, 2026`, `Oct 12 2027`, and `5/10/2026`.

Calendar exports include calendar metadata, UTC timestamps, and stable event IDs based on each event's name and date. Identical names and dates share an ID, including across courses; editing either produces a new ID. Import behavior depends on the calendar app, so repeated imports are not guaranteed to avoid duplicates.

PDF extraction preserves page layout and joins wrapped cells in weekly schedule tables. Bordered tables with a Date column and one date per row keep the whole topic cell attached to that date, including vertically centered dates. Exam headings are carried into section-specific dates, and conditional or example dates are left unselected for review. Exam windows written with full start and end dates are shown as one all-day event on the closing date, with the date range in its name. Consult the syllabus for exact opening and closing times.

Possible repeated exam summaries are left unchecked when a section-specific entry already names that assessment on the same date. They remain available with an explanation so you can include them if they represent a separate event. Different sections and exam numbers stay separate.

Scanned pages without readable text are not processed. If a PDF also has readable pages, the review identifies the skipped page numbers; a fully scanned PDF asks you to paste the text instead. OCR is not included.

Always review the results: unusual or borderless tables, abbreviated date ranges, and repeated events described differently can still require manual correction. If a syllabus lists several course sections, select the events for your section.

## Project structure

| File | Role |
| --- | --- |
| `app.py` | Flask routes: upload/paste form, review page, `.ics` download |
| `parser.py` | Finds dates in syllabus text and classifies each event |
| `pdf_text.py` | Extracts PDF text and table rows, and identifies skipped image pages |
| `calendar_maker.py` | Writes events to `.ics` format |
| `templates/`, `static/` | HTML pages and styling |
| `tests/` | Pytest suite covering the parser, calendar output, and web routes |

## Run it locally

```bash
git clone https://github.com/amenb106-blip/syllabussync.git
cd syllabussync
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000.

To enable Flask's debugger and auto-reload while developing, set `FLASK_DEBUG=1` before starting the app.

## Run the tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

## Built with

Python, Flask, pypdf, pdfplumber, icalendar, pytest. Deployed on Vercel.
