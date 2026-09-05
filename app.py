import io
import os
from datetime import date, time

from flask import Flask, request, render_template, send_file

from parser import parse_syllabus
from calendar_maker import make_calendar
from pdf_text import read_pdf_text

app = Flask(__name__)


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

@app.route("/")
def home():
    return render_template("index.html", current_year=date.today().year)


@app.route("/generate", methods=["POST"])
def generate():
    academic_start_year = get_academic_start_year()
    if academic_start_year is None:
        return message_page("Choose a valid academic start year between 2000 and 2100.")

    uploaded_pdf = request.files.get("pdf")
    skipped_pages = []
    pdf_warning = None

    if uploaded_pdf and uploaded_pdf.filename:
        try:
            syllabus_text = read_pdf_text(uploaded_pdf, skipped_pages=skipped_pages)
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
        if skipped_pages:
            page_numbers = ", ".join(str(number) for number in skipped_pages)
            page_label = "page" if len(skipped_pages) == 1 else "pages"
            verb = "was" if len(skipped_pages) == 1 else "were"
            pdf_warning = (
                f"PDF {page_label} {page_numbers} {verb} skipped because no readable text was found in the images. "
                "This event list may be incomplete. Check those pages in your PDF or paste their text."
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
            + (f" {pdf_warning}" if pdf_warning else "")
        )

    return render_template("review.html", groups=group_events(events), pdf_warning=pdf_warning)


@app.route("/download", methods=["POST"])
def download():
    names = request.form.getlist("name")
    date_values = request.form.getlist("event_date")
    time_values = request.form.getlist("event_time")
    selected_values = request.form.getlist("include")

    if len(names) != len(date_values) or (time_values and len(names) != len(time_values)):
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

        time_value = (time_values[index] if index < len(time_values) else "").strip()
        try:
            event_time = time.fromisoformat(time_value) if time_value else None
        except ValueError:
            return message_page("Every included event needs a valid time, or no time at all.")

        if not event_name:
            return message_page("Every included event needs a name.")
        events.append({"name": event_name, "date": event_date, "time": event_time})

    if not events:
        return message_page("Select at least one event to create a calendar.")

    return send_file(
        io.BytesIO(make_calendar(events)),
        mimetype="text/calendar",
        as_attachment=True,
        download_name="syllabus.ics",
    )


if __name__ == "__main__":

    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
