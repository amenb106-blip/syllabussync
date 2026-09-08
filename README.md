# SyllabusSync

Turn a course syllabus into a calendar file, using AI to find the dates.

Paste your syllabus text or upload the PDF. SyllabusSync uses Google Gemini to pull out the exams, assignments, and due dates, lets you review and edit them, then gives you an `.ics` file you can import into Google Calendar, Apple Calendar, or Outlook.

## How it works

1. **Add a syllabus** – paste the text or upload a PDF with selectable text, and choose the academic start year.
2. **Find events** – the app sends the syllabus text to Gemini, which returns the events it found: a short title, a date, an optional time, and a category (Assessments, Deadlines, Readings, and so on).
3. **Review** – events are grouped by category. Clear deadlines and assessments are pre-selected; you can fix names, dates, and times or untick anything that doesn't belong.
4. **Download** – the selected events are written to a standard `.ics` file. Events with a time use that local clock time; events without a time stay all-day.

Dates from August–December use the academic start year; January–July roll forward to the next year. A four-digit year written in the syllabus takes priority.

Always review the results before downloading — the AI can miss or misread items, and you get the final say on what ends up in your calendar.

## Requirements

The app uses the Gemini API, so you need a free API key from [Google AI Studio](https://aistudio.google.com/apikey).

## Run it locally

```bash
git clone https://github.com/amenb106-blip/syllabussync.git
cd syllabussync
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux
pip install -r requirements-dev.txt
```

Set your API key and start the app. PowerShell:

```powershell
$env:GEMINI_API_KEY = "your-key"; $env:SYLLABUS_AI = "1"; python app.py
```

macOS / Linux:

```bash
GEMINI_API_KEY="your-key" SYLLABUS_AI="1" python app.py
```

Then open http://127.0.0.1:5000. The key is read from the environment and is never written to a file. Add `FLASK_DEBUG=1` to enable auto-reload while developing.

## Project structure

| File | Role |
| --- | --- |
| `app.py` | Flask routes: upload/paste form, review page, `.ics` download |
| `extractor.py` | Sends syllabus text to Gemini and returns structured events |
| `config.py` | Reads settings (API key, model) from the environment |
| `pdf_text.py` | Extracts PDF text and table rows, and identifies skipped image pages |
| `calendar_maker.py` | Writes events to `.ics` format |
| `templates/`, `static/` | HTML pages and styling |
| `tests/` | Pytest suite covering the web routes, extraction, and calendar output |

## Run the tests

```bash
python -m pytest
```

The tests mock the Gemini call, so they run without an API key.

## Built with

Python, Flask, google-genai (Gemini), pypdf, pdfplumber, icalendar, pytest.
