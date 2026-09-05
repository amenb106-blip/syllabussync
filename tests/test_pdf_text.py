import io
from datetime import date
from html.parser import HTMLParser

from icalendar import Calendar
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from werkzeug.datastructures import MultiDict

from app import app
from pdf_text import read_pdf_text


def syllabus_pdf():
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Courier"),
    })
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})
    })
    rows = [
        (30, 740, "Final exam"),
        (30, 725, "Section 001: December 17, 2025 in class"),
        (30, 700, "For example, an assignment due September 3 could be submitted late."),
        (30, 650, "Week"), (90, 650, "Topics"),
        (300, 650, "Deliverables"), (480, 650, "Activities"),
        (30, 630, "1"), (90, 630, "Data storage"),
        (300, 630, "Term Project"), (480, 630, "Quiz"),
        (300, 615, "Proposal"), (300, 600, "submission (11/4)"),
        (30, 580, "2"), (90, 580, "Databases"),
        (300, 580, "Final Term Project"), (480, 580, "Quiz"),
        (300, 565, "report and software"), (300, 550, "submission (12/4)"),
        (30, 510, "Course Policy"),
        (30, 495, "Office hours: October 6"),
    ]
    commands = []
    for x, y, text in rows:
        escaped = text.replace("(", r"\(").replace(")", r"\)")
        commands.append(f"BT /F1 8 Tf {x} {y} Td ({escaped}) Tj ET")
    stream = DecodedStreamObject()
    stream.set_data("\n".join(commands).encode("ascii"))
    page[NameObject("/Contents")] = stream
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class FormParser(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.fields = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "input" and "name" in attrs:
            if attrs.get("type") != "checkbox" or "checked" in attrs:
                self.fields.append((attrs["name"], attrs.get("value", "")))


def test_real_pdf_upload_preserves_table_names_and_excludes_policy_examples():
    pdf = syllabus_pdf()
    extracted = read_pdf_text(io.BytesIO(pdf))
    assert "Term Project Proposal submission (11/4)" in extracted
    assert "Final Term Project report and software submission (12/4)" in extracted

    with app.test_client() as client:
        review = client.post("/generate", data={
            "academic_start_year": "2025",
            "pdf": (io.BytesIO(pdf), "syllabus.pdf"),
        })
        assert review.status_code == 200
        fields = FormParser(review.get_data(as_text=True)).fields
        download = client.post("/download", data=MultiDict(fields))

    assert download.status_code == 200
    assert download.mimetype == "text/calendar"
    events = Calendar.from_ical(download.data).walk("VEVENT")
    assert {(str(event["SUMMARY"]), event.decoded("DTSTART")) for event in events} == {
        ("Final exam: Section 001: in class", date(2025, 12, 17)),
        ("Term Project Proposal submission", date(2025, 11, 4)),
        ("Final Term Project report and software submission", date(2025, 12, 4)),
    }
