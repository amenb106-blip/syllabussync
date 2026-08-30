# How to Run SyllabusSync

For the finished-product explanation, read [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md).

## Start the app

In PowerShell, from this project folder:

```powershell
.\venv\Scripts\Activate.ps1
python app.py
```

Open the local address Flask prints, normally `http://127.0.0.1:5000`.

## Use the app

1. Paste syllabus text or upload a text-based PDF.
2. Choose the academic year's starting year.
3. Select **Find Events**.
4. Edit event names or dates, and uncheck events you do not want.
5. Select **Download Calendar** and import `syllabus.ics` into your calendar app.

## Run the tests

```powershell
.\venv\Scripts\python.exe -m pytest -q
```

The test suite checks the parser, generated calendar files, and the important browser workflow.
