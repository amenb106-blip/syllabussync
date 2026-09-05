# SyllabusSync

Turn a course syllabus into a calendar file.

**Live app:** https://syllabussync-sand.vercel.app

Paste your syllabus text or upload the PDF. SyllabusSync finds the exams, assignments, and due dates, lets you review and edit them, then gives you an `.ics` file you can import into Google Calendar, Apple Calendar, or Outlook.

## How it works

1. **Add a syllabus** – paste the text or upload a PDF with selectable text, and choose the academic start year.
2. **Find dates** – the parser scans each line for dates like `October 12`, `Oct 12`, or `10/12` and uses the surrounding text as the event name.
3. **Review** – events are grouped (Assessments, Deadlines, Readings, etc.). Clear deadlines are pre-selected; you can fix names and dates or untick anything that doesn't belong.
4. **Download** – the selected events are written to a standard `.ics` file as all-day events.

Dates from August–December use the chosen start year; January–July roll forward to the next year, so a Fall 2026 / Spring 2027 course just needs `2026`.

## Project structure

| File | Role |
| --- | --- |
| `app.py` | Flask routes: upload/paste form, review page, `.ics` download |
| `parser.py` | Finds dates in syllabus text and classifies each event |
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

Python, Flask, pypdf, icalendar, pytest. Deployed on Vercel.
