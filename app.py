import io
import os
from datetime import date, time

from flask import Flask, request, render_template, send_file, jsonify

from extractor import extract_events
from calendar_maker import make_calendar
from pdf_text import read_pdf_text

app = Flask(__name__)

REMINDER_CHOICES = ("", "15", "60", "1440")
UNREADABLE_EVENTS = "Your event list could not be read. Please generate it again."


class RequestError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


@app.context_processor
def static_asset_version():
    def asset_version(filename):
        try:
            return int(os.path.getmtime(os.path.join(app.static_folder, filename)))
        except OSError:
            return 0

    return {"asset_version": asset_version}


def message_page(text):
    return render_template("error.html", text=text)


def get_academic_start_year():
    try:
        academic_start_year = int(request.form.get("academic_start_year", ""))
    except ValueError:
        return None

    if not 2000 <= academic_start_year <= 2100:
        return None
    return academic_start_year


def read_uploaded_pdf(uploaded_pdf, skipped_pages):
    if not uploaded_pdf.filename.lower().endswith(".pdf"):
        raise RequestError("Choose a PDF file.")

    try:
        text = read_pdf_text(uploaded_pdf, skipped_pages=skipped_pages)
    except Exception:
        raise RequestError("Unable to read that file. Make sure it is a readable PDF, or paste its text.")

    if not text.strip():
        raise RequestError("This PDF has no readable text. Paste the syllabus text instead.")
    return text


def skipped_pages_warning(skipped_pages):
    page_numbers = ", ".join(str(number) for number in skipped_pages)
    page_label = "page" if len(skipped_pages) == 1 else "pages"
    verb = "was" if len(skipped_pages) == 1 else "were"
    return (
        f"PDF {page_label} {page_numbers} {verb} skipped because no readable text was found in the images. "
        "This event list may be incomplete. Check those pages in your PDF or paste their text."
    )


def process_syllabus():
    academic_start_year = get_academic_start_year()
    if academic_start_year is None:
        raise RequestError("Choose a valid academic start year between 2000 and 2100.")

    uploaded_pdf = request.files.get("pdf")
    pdf_warning = None

    if uploaded_pdf and uploaded_pdf.filename:
        skipped_pages = []
        syllabus_text = read_uploaded_pdf(uploaded_pdf, skipped_pages)
        if skipped_pages:
            pdf_warning = skipped_pages_warning(skipped_pages)
    else:
        syllabus_text = request.form.get("syllabus", "")

    if not syllabus_text.strip():
        raise RequestError("Upload a PDF or paste syllabus text.")

    try:
        events = extract_events(syllabus_text, academic_start_year)
    except Exception:
        raise RequestError("Unable to extract events. Try again shortly.", 502)
    return events, pdf_warning


def group_events(events):
    grouped = {}
    for event in events:
        grouped.setdefault(event["category"], []).append(event)

    result = []
    render_index = 0
    for category, items in grouped.items():
        numbered_items = []
        for event in items:
            numbered_items.append({"index": render_index, **event})
            render_index += 1
        result.append({
            "label": category,
            "items": numbered_items,
            "all_selected": all(item["default_selected"] for item in numbered_items),
        })
    return result


def serialize_event(event):
    return {
        **event,
        "date": event["date"].isoformat(),
        "time": event["time"].isoformat(timespec="minutes") if event.get("time") else None,
    }


def selected_indexes(values, event_count):
    indexes = set()
    for value in values:
        try:
            index = int(value)
        except ValueError:
            raise RequestError(UNREADABLE_EVENTS)
        if not 0 <= index < event_count:
            raise RequestError(UNREADABLE_EVENTS)
        indexes.add(index)
    return sorted(indexes)


def selected_events(form):
    names = form.getlist("name")
    date_values = form.getlist("event_date")
    time_values = form.getlist("event_time")

    if len(names) != len(date_values) or (time_values and len(names) != len(time_values)):
        raise RequestError(UNREADABLE_EVENTS)

    events = []
    for index in selected_indexes(form.getlist("include"), len(names)):
        event_name = names[index].strip()
        try:
            event_date = date.fromisoformat(date_values[index])
        except ValueError:
            raise RequestError("Every included event needs a valid date.")

        time_value = (time_values[index] if index < len(time_values) else "").strip()
        try:
            event_time = time.fromisoformat(time_value) if time_value else None
        except ValueError:
            raise RequestError("Every included event needs a valid time, or no time at all.")

        if not event_name:
            raise RequestError("Every included event needs a name.")
        events.append({"name": event_name, "date": event_date, "time": event_time})
    return events


@app.route("/")
def home():
    return render_template("index.html", current_year=date.today().year)


@app.route("/api/extract", methods=["POST"])
def api_extract():
    try:
        events, warning = process_syllabus()
    except RequestError as error:
        return jsonify(error={"message": error.message}), error.status

    return jsonify(
        events=[serialize_event(event) for event in events],
        warnings=[warning] if warning else [],
    )


@app.route("/generate", methods=["POST"])
def generate():
    try:
        events, pdf_warning = process_syllabus()
    except RequestError as error:
        return message_page(error.message)

    if not events:
        return message_page(
            "No dated events found. Check the syllabus or try another file."
            + (f" {pdf_warning}" if pdf_warning else "")
        )

    return render_template("review.html", groups=group_events(events), pdf_warning=pdf_warning)


@app.route("/download", methods=["POST"])
def download():
    reminder_value = request.form.get("reminder_minutes", "")
    if reminder_value not in REMINDER_CHOICES:
        return message_page("Choose a valid reminder interval."), 400

    try:
        events = selected_events(request.form)
    except RequestError as error:
        return message_page(error.message)

    if not events:
        return message_page("Select at least one event to create a calendar.")

    calendar = make_calendar(events, reminder_minutes=int(reminder_value) if reminder_value else None)
    return send_file(
        io.BytesIO(calendar),
        mimetype="text/calendar",
        as_attachment=True,
        download_name="syllabus.ics",
    )


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
