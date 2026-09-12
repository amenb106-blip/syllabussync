# SyllabusSync

A document-to-calendar workspace built with Flask, Jinja, and vanilla JavaScript.

## How it works

1. **Upload** one or more PDFs with selectable text, or paste syllabus text. Choose the academic start year.
2. **Extract** events with Google Gemini. Files are processed sequentially; failed documents can be retried without losing successful results.
3. **Review** the schedule. Edit titles, dates, and optional times, select categories or individual events, and remove events with Undo. Additional documents preserve existing edits.
4. **Export** selected events to `.ics`, with an optional reminder (15 minutes, 1 hour, or 1 day before). Individual Google Calendar links open event drafts with your edits; those drafts use Google Calendar's reminder settings.

Dates from August through December use the academic start year; January through July roll forward to the next year. A four-digit year in the syllabus takes priority. Blank times remain all-day; timed events use local clock time. All-day reminders are relative to the start of the day.

Review extracted dates against the source syllabus. Session state stays in browser memory and resets on reload. SyllabusSync does not save uploaded files; extracted text is sent to Google Gemini.

## Interfaces

- `POST /api/extract`: multipart form with one `pdf` or `syllabus` text, plus `academic_start_year`. Returns `events` (ISO date/time strings) and `warnings`; failures return an `error.message` with HTTP 400 or 502.
- `POST /generate`: compatible server-rendered upload/review flow.
- `POST /download`: existing repeated `name`, `event_date`, `event_time`, and indexed `include` fields, plus optional `reminder_minutes` (`15`, `60`, `1440`, or empty).

## Requirements

The app uses the Gemini API, so you need a free API key from [Google AI Studio](https://aistudio.google.com/apikey).

## Run it locally

```bash
git clone https://github.com/amenb106-blip/syllabussync.git
cd syllabussync
python -m venv venv
```

Activate the environment in PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Or on macOS / Linux:

```bash
source venv/bin/activate
```

Install the dependencies:

```bash
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
| `templates/`, `static/` | Dashboard, browser workflow, styling, and bundled Sora/Manrope fonts |
| `tests/` | Pytest suite covering the web routes, extraction, and calendar output |

## Run the tests

```bash
python -m pytest
node --test tests/dashboard.test.cjs
```

The tests mock the Gemini call, so they run without an API key.

## Built with

Python, Flask, google-genai (Gemini), pypdf, pdfplumber, icalendar, pytest.

## Browser checks

With the app running locally, install Playwright in your development environment and run:

```bash
node tests/dashboard.browser.cjs
```

The browser checks use installed Google Chrome, mock extraction (no Gemini key required), and exercise real calendar downloads at 1440, 1024, 390, and 320 pixels. Set `BASE_URL` to test another local port and `SCREENSHOT_DIR` to choose the screenshot output directory. By default, screenshots go to a `syllabussync-screenshots` directory in the operating system's temporary folder.
