import io
from datetime import date, datetime
from html.parser import HTMLParser

from icalendar import Calendar
import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject, NumberObject
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
    page[NameObject("/Contents")] = writer._add_object(stream)
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


def dated_table_pdf(first_date_y, second_date_y):
    writer = PdfWriter()
    page = writer.add_page(PdfReader(io.BytesIO(syllabus_pdf())).pages[0])
    rows = [
        (30, 705, "DATE"), (180, 705, "TOPIC"), (460, 705, "READING"),
        (30, first_date_y, "Week 5 - 9/17"),
        (180, 680, "Exam 1"), (180, 665, "Class discussion"),
        (460, 680, "Chapter 5"),
        (30, second_date_y, "Week 10 - 10/22"),
        (180, 570, "Final Term Project"), (180, 555, "Submission due at the start of class"),
        (460, 570, "Chapter 10"),
        (30, 400, "Homework due November 3"),
    ]
    commands = [f"BT /F1 8 Tf {x} {y} Td ({text}) Tj ET" for x, y, text in rows]
    commands.extend(f"{x} 450 m {x} 720 l S" for x in (28, 175, 455, 580))
    commands.extend(f"28 {y} m 580 {y} l S" for y in (450, 590, 700, 720))
    stream = DecodedStreamObject()
    stream.set_data("\n".join(commands).encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


@pytest.mark.parametrize("first_date_y, second_date_y", [(680, 570), (640, 510), (605, 465)])
def test_dated_table_rows_keep_dates_with_their_full_description(first_date_y, second_date_y):
    pdf = dated_table_pdf(first_date_y, second_date_y)
    with app.test_client() as client:
        review = client.post("/generate", data={
            "academic_start_year": "2025", "pdf": (io.BytesIO(pdf), "table.pdf"),
        })
        assert review.status_code == 200
        download = client.post("/download", data=MultiDict(FormParser(review.get_data(as_text=True)).fields))
    assert download.mimetype == "text/calendar"
    events = Calendar.from_ical(download.data).walk("VEVENT")
    assert {(str(event["SUMMARY"]), event.decoded("DTSTART")) for event in events} == {
        ("Exam 1 Class discussion", date(2025, 9, 17)),
        ("Final Term Project Submission due at the start of class", date(2025, 10, 22)),
        ("Homework", date(2025, 11, 3)),
    }


def pdf_with_image_page(*, include_text=False, blank=False):
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    if not blank:
        bitmap = DecodedStreamObject()
        bitmap.set_data(b"\x00\xff\xff\x00")
        bitmap.update({
            NameObject("/Type"): NameObject("/XObject"),
            NameObject("/Subtype"): NameObject("/Image"),
            NameObject("/Width"): NumberObject(2),
            NameObject("/Height"): NumberObject(2),
            NameObject("/ColorSpace"): NameObject("/DeviceGray"),
            NameObject("/BitsPerComponent"): NumberObject(8),
        })
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/XObject"): DictionaryObject({NameObject("/Im0"): writer._add_object(bitmap)})
        })
        stream = DecodedStreamObject()
        stream.set_data(b"q 612 0 0 792 0 0 cm /Im0 Do Q")
        page[NameObject("/Contents")] = writer._add_object(stream)
    if include_text:
        writer.add_page(PdfReader(io.BytesIO(syllabus_pdf())).pages[0])
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def test_mixed_pdf_warns_about_skipped_pages_and_still_exports_readable_events():
    pdf = pdf_with_image_page(include_text=True)
    with app.test_client() as client:
        review = client.post("/generate", data={
            "academic_start_year": "2025", "pdf": (io.BytesIO(pdf), "mixed.pdf"),
        })
        html = review.get_data(as_text=True)
        assert 'role="alert"' in html
        assert "PDF page 1 was skipped" in html
        assert "This event list may be incomplete" in html
        download = client.post("/download", data=MultiDict(FormParser(html).fields))
    assert download.mimetype == "text/calendar"
    assert len(Calendar.from_ical(download.data).walk("VEVENT")) == 3


def test_image_only_pdf_reports_no_readable_text():
    with app.test_client() as client:
        response = client.post("/generate", data={
            "academic_start_year": "2025", "pdf": (io.BytesIO(pdf_with_image_page()), "scan.pdf"),
        })
    assert b"contain any readable text" in response.data
    assert b"Review your events" not in response.data


def test_blank_pages_do_not_trigger_a_scan_warning():
    with app.test_client() as client:
        response = client.post("/generate", data={
            "academic_start_year": "2025",
            "pdf": (io.BytesIO(pdf_with_image_page(include_text=True, blank=True)), "blank-page.pdf"),
        })
    assert b"Review your events" in response.data
    assert b"skipped" not in response.data


def test_mixed_pdf_with_no_dates_still_reports_skipped_pages():
    writer = PdfWriter()
    writer.append(PdfReader(io.BytesIO(pdf_with_image_page(include_text=True))))
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 8 Tf 30 700 Td (Welcome to the course) Tj ET")
    writer.pages[1][NameObject("/Contents")] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    with app.test_client() as client:
        response = client.post("/generate", data={
            "academic_start_year": "2025", "pdf": (io.BytesIO(output.getvalue()), "mixed.pdf"),
        })
    assert b"find any dates" in response.data
    assert b"PDF page 1 was skipped" in response.data


def text_page_pdf(rows, lines=(), extra=""):
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Courier"),
    })
    resources = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})
    })
    commands = [f"BT /F1 8 Tf {x} {y} Td ({text}) Tj ET" for x, y, text in rows]
    commands.extend(lines)
    stream = DecodedStreamObject()
    stream.set_data((extra + "\n".join(commands)).encode("ascii"))
    page[NameObject("/Resources")] = resources
    page[NameObject("/Contents")] = writer._add_object(stream)
    return writer, page


def split_deadline_table_pdf():
    rows = [
        (30, 705, "Date / Week"), (180, 705, "Topic Covered"), (460, 705, "Assignments"),
        (30, 680, "Oct 12, 2026"), (180, 680, "Midterm Examination"), (460, 680, "Exam on Oct 14"),
        (30, 570, "Oct 19, 2026"), (180, 570, "Lists and Dictionaries"), (460, 570, "Lab 3 Due"),
    ]
    rules = [f"{x} 450 m {x} 720 l S" for x in (28, 175, 455, 580)]
    rules.extend(f"28 {y} m 580 {y} l S" for y in (450, 590, 700, 720))
    writer, _ = text_page_pdf(rows, rules)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def test_deadline_column_events_are_kept_alongside_the_topic_column():
    with app.test_client() as client:
        review = client.post("/generate", data={
            "academic_start_year": "2026",
            "pdf": (io.BytesIO(split_deadline_table_pdf()), "table.pdf"),
        })
        assert review.status_code == 200
        download = client.post(
            "/download", data=MultiDict(FormParser(review.get_data(as_text=True)).fields)
        )

    events = Calendar.from_ical(download.data).walk("VEVENT")
    assert {(str(event["SUMMARY"]), event.decoded("DTSTART")) for event in events} == {
        ("Midterm Examination", date(2026, 10, 12)),
        ("Exam", date(2026, 10, 14)),
        ("Lab 3", date(2026, 10, 19)),
    }


def scanned_page_with_footer_pdf():
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    bitmap = DecodedStreamObject()
    bitmap.set_data(b"\x00\xff\xff\x00")
    bitmap.update({
        NameObject("/Type"): NameObject("/XObject"),
        NameObject("/Subtype"): NameObject("/Image"),
        NameObject("/Width"): NumberObject(2),
        NameObject("/Height"): NumberObject(2),
        NameObject("/ColorSpace"): NameObject("/DeviceGray"),
        NameObject("/BitsPerComponent"): NumberObject(8),
    })
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Courier"),
    })
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/XObject"): DictionaryObject({NameObject("/Im0"): writer._add_object(bitmap)}),
        NameObject("/Font"): DictionaryObject({NameObject("/F1"): font}),
    })
    stream = DecodedStreamObject()
    stream.set_data(
        b"q 612 0 0 792 0 0 cm /Im0 Do Q\n"
        b"BT /F1 8 Tf 250 24 Td (Biology 101 Syllabus - Page 1 of 2) Tj ET"
    )
    page[NameObject("/Contents")] = writer._add_object(stream)
    writer.add_page(PdfReader(io.BytesIO(syllabus_pdf())).pages[0])
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def test_scanned_page_with_a_readable_footer_is_still_reported_as_skipped():
    with app.test_client() as client:
        response = client.post("/generate", data={
            "academic_start_year": "2025",
            "pdf": (io.BytesIO(scanned_page_with_footer_pdf()), "scan-with-footer.pdf"),
        })

    html = response.get_data(as_text=True)
    assert "PDF page 1 was skipped" in html
    assert "This event list may be incomplete" in html


def test_uploaded_pdf_carries_a_parsed_time_through_to_the_calendar():
    rows = [
        (30, 740, "Lab 1 Due: December 17, 2025 at 11:59 PM"),
        (30, 720, "Midterm Examination: December 4, 2025"),
    ]
    writer, _ = text_page_pdf(rows)
    output = io.BytesIO()
    writer.write(output)

    with app.test_client() as client:
        review = client.post("/generate", data={
            "academic_start_year": "2025", "pdf": (io.BytesIO(output.getvalue()), "times.pdf"),
        })
        assert review.status_code == 200
        download = client.post(
            "/download", data=MultiDict(FormParser(review.get_data(as_text=True)).fields)
        )

    events = {
        str(event["SUMMARY"]): event.decoded("DTSTART")
        for event in Calendar.from_ical(download.data).walk("VEVENT")
    }
    assert events["Lab 1"] == datetime(2025, 12, 17, 23, 59)
    assert events["Midterm Examination"] == date(2025, 12, 4)
