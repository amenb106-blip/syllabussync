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


def test_real_pdf_upload_preserves_table_names():
    extracted = read_pdf_text(io.BytesIO(syllabus_pdf()))
    assert "Term Project Proposal submission (11/4)" in extracted
    assert "Final Term Project report and software submission (12/4)" in extracted
    assert "Section 001: December 17, 2025 in class" in extracted


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
    extracted = read_pdf_text(io.BytesIO(dated_table_pdf(first_date_y, second_date_y)))
    assert "9/17 - Exam 1 Class discussion" in extracted
    assert "10/22 - Final Term Project Submission due at the start of class" in extracted
    assert "Homework due November 3" in extracted


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


def test_mixed_pdf_detects_the_scanned_page_and_keeps_readable_text():
    skipped = []
    extracted = read_pdf_text(
        io.BytesIO(pdf_with_image_page(include_text=True)), skipped_pages=skipped
    )
    assert skipped == [1]
    assert "Term Project Proposal submission (11/4)" in extracted


def test_image_only_pdf_reports_no_readable_text():
    with app.test_client() as client:
        response = client.post("/generate", data={
            "academic_start_year": "2025", "pdf": (io.BytesIO(pdf_with_image_page()), "scan.pdf"),
        })
    assert b"no readable text" in response.data
    assert b"Review your events" not in response.data


def test_blank_image_page_does_not_trigger_a_scan_warning():
    skipped = []
    read_pdf_text(
        io.BytesIO(pdf_with_image_page(include_text=True, blank=True)), skipped_pages=skipped
    )
    assert skipped == []


def test_mixed_pdf_with_no_dates_still_reports_skipped_pages():
    writer = PdfWriter()
    writer.append(PdfReader(io.BytesIO(pdf_with_image_page(include_text=True))))
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 8 Tf 30 700 Td (Welcome to the course) Tj ET")
    writer.pages[1][NameObject("/Contents")] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    skipped = []
    extracted = read_pdf_text(io.BytesIO(output.getvalue()), skipped_pages=skipped)
    assert skipped == [1]
    assert "Welcome to the course" in extracted


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


def test_deadline_column_is_kept_alongside_the_topic_column():
    extracted = read_pdf_text(io.BytesIO(split_deadline_table_pdf()))
    assert "Oct 12, 2026 - Midterm Examination" in extracted
    assert "Exam on Oct 14" in extracted
    assert "Oct 19, 2026 - Lab 3 Due" in extracted


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
    skipped = []
    read_pdf_text(io.BytesIO(scanned_page_with_footer_pdf()), skipped_pages=skipped)
    assert skipped == [1]


def test_uploaded_pdf_carries_a_parsed_time_through_to_the_calendar():
    rows = [
        (30, 740, "Lab 1 Due: December 17, 2025 at 11:59 PM"),
        (30, 720, "Midterm Examination: December 4, 2025"),
    ]
    writer, _ = text_page_pdf(rows)
    output = io.BytesIO()
    writer.write(output)

    extracted = read_pdf_text(io.BytesIO(output.getvalue()))
    assert "Lab 1 Due: December 17, 2025 at 11:59 PM" in extracted
    assert "Midterm Examination: December 4, 2025" in extracted


def test_pdf_word_spacing_preserves_months_and_exam_times_in_calendar_output():
    writer, page = text_page_pdf([])
    page["/Resources"]["/Font"]["/F1"][NameObject("/BaseFont")] = NameObject("/Times-Roman")
    stream = DecodedStreamObject()
    stream.set_data(
        b"BT /F1 12 Tf 30 740 Td [(Writing Assignment 2 due Novem) -166.667 (ber 14, 2025)] TJ ET\n"
        b"BT /F1 12 Tf 30 710 Td [(The midterm is an assembly exam scheduled for 8) -166.667 "
        b"(:20-9:30PM on October 8th.)] TJ ET"
    )
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)

    extracted = read_pdf_text(io.BytesIO(output.getvalue()))
    assert "Writing Assignment 2 due November 14, 2025" in extracted
    assert "8:20-9:30PM on October 8th." in extracted


def test_pdf_exam_windows_export_closing_times():
    writer, _ = text_page_pdf([
        (30, 740, "Midterm"),
        (30, 725, "Section 801/802: Online exam between 4:00PM October 12, 2025 and"),
        (30, 710, "3:59PM October 13, 2025. Students may take the exam in this window."),
        (30, 680, "Final exam"),
        (30, 665, "Section 801/802: Online exam between 11:50AM December 17, 2025 --"),
        (30, 650, "11:49AM December 18, 2025"),
    ])
    output = io.BytesIO()
    writer.write(output)

    extracted = read_pdf_text(io.BytesIO(output.getvalue()))
    assert "3:59PM October 13, 2025" in extracted
    assert "11:49AM December 18, 2025" in extracted


def test_weekly_table_headers_with_multiple_words_keep_wrapped_project_names():
    reader = PdfReader(io.BytesIO(syllabus_pdf()))
    writer = PdfWriter()
    page = writer.add_page(reader.pages[0])
    stream = DecodedStreamObject()
    stream.set_data(
        page.get_contents().get_data()
        .replace(b"(Deliverables)", b"(Key Deliverables)")
        .replace(b"(Activities)", b"(In-class Activities)")
    )
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)

    extracted = read_pdf_text(io.BytesIO(output.getvalue()))
    assert "Term Project Proposal submission (11/4)" in extracted
    assert "Final Term Project report and software submission (12/4)" in extracted
