import io
from collections import OrderedDict
from datetime import date

from flask import Flask, request, render_template, send_file

from parser import parse_syllabus
from calendar_maker import make_calendar
from pypdf import PdfReader

app = Flask(__name__)


def message_page(text):
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>SyllabusSync</title>"
        '<link rel="stylesheet" href="/static/style.css">'
        '</head><body><main class="container">'
        f'<h1>SyllabusSync</h1><p class="message">{text}</p>'
        '<p><a href="/">Go back</a></p>'
        "</main></body></html>"
    )


def get_academic_start_year():
    """Read and validate the academic-year start chosen in the form."""
    try:
        academic_start_year = int(request.form.get("academic_start_year", ""))
    except ValueError:
        return None

    if not 2000 <= academic_start_year <= 2100:
        return None
    return academic_start_year


def read_pdf_text(uploaded_file):
    reader = PdfReader(uploaded_file)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def group_events(events):
    """Keep related review candidates together while preserving source order."""
    grouped = OrderedDict()
    for index, event in enumerate(events):
        grouped.setdefault(event["category"], []).append({"index": index, **event})

    return [
        {
            "label": category,
            "items": items,
            "all_selected": all(item["default_selected"] for item in items),
        }
        for category, items in grouped.items()
    ]


@app.route("/")
def home():
    return render_template("index.html", current_year=date.today().year)


@app.route("/generate", methods=["POST"])
def generate():
    academic_start_year = get_academic_start_year()
    if academic_start_year is None:
        return message_page("Choose a valid academic start year between 2000 and 2100.")

    uploaded_pdf = request.files.get("pdf")

    if uploaded_pdf and uploaded_pdf.filename:
        try:
            syllabus_text = read_pdf_text(uploaded_pdf)
        except Exception:
            return message_page(
                "We couldn't read that file. Make sure it's a PDF, "
                "or paste your syllabus text into the box instead."
            )

        if not syllabus_text.strip():
            return message_page(
                "That PDF doesn't contain any readable text - it looks like "
                "a scan or a picture. Please copy your syllabus and paste it "
                "into the text box instead."
            )
    else:
        syllabus_text = request.form.get("syllabus", "")

    if not syllabus_text.strip():
        return message_page(
            "You didn't give us anything to read. Paste your syllabus "
            "into the box, or upload a PDF."
        )

    events = parse_syllabus(syllabus_text, academic_start_year)
    if not events:
        return message_page(
            "We couldn't find any dates in that syllabus. We understand "
            'formats like "October 12", "Oct 12" and "10/5".'
        )

    return render_template("review.html", groups=group_events(events))


@app.route("/download", methods=["POST"])
def download():
    names = request.form.getlist("name")
    date_values = request.form.getlist("event_date")
    selected_values = request.form.getlist("include")

    if len(names) != len(date_values):
        return message_page("Your event list could not be read. Please generate it again.")

    events = []
    selected_indexes = set()
    for value in selected_values:
        try:
            index = int(value)
        except ValueError:
            return message_page("Your event list could not be read. Please generate it again.")
        if not 0 <= index < len(names):
            return message_page("Your event list could not be read. Please generate it again.")
        selected_indexes.add(index)

    for index in sorted(selected_indexes):
        event_name = names[index].strip()
        try:
            event_date = date.fromisoformat(date_values[index])
        except ValueError:
            return message_page("Every included event needs a valid date.")

        if not event_name:
            return message_page("Every included event needs a name.")
        events.append({"name": event_name, "date": event_date})

    if not events:
        return message_page("Select at least one event to create a calendar.")

    return send_file(
        io.BytesIO(make_calendar(events)),
        mimetype="text/calendar",
        as_attachment=True,
        download_name="syllabus.ics",
    )


if __name__ == "__main__":
    app.run(debug=True)
