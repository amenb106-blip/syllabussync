# SyllabusSync — Project Overview

## What it is

SyllabusSync is a web app that turns a college course syllabus into a calendar file.

Instead of reading every deadline and entering it manually into Google Calendar, a student can paste the syllabus text or upload its PDF. SyllabusSync finds the important dates, lets the student check them, and creates a calendar file they can import.

## The problem it solves

Students often receive several syllabi at the beginning of a term. Each syllabus can include quizzes, exams, projects, readings, and assignment deadlines. Entering all of those dates by hand is slow, repetitive, and easy to get wrong.

SyllabusSync makes that process faster:

1. Give the app a syllabus.
2. Let it find possible deadlines.
3. Review and correct the results.
4. Download a calendar file.
5. Import that file into Google Calendar, Apple Calendar, or Outlook.

## What a finished user experience looks like

### 1. Add a syllabus

The student opens the website and either:

- pastes the text from a syllabus, or
- uploads a PDF that contains selectable text.

They also choose the academic year. For example, a Fall 2026–Spring 2027 course would start with `2026`.

### 2. Find dates and events

The app reads the syllabus line by line and looks for date formats such as:

- `October 12`
- `Oct 12`
- `10/12`

If it sees a line like `Midterm Exam: October 12`, it treats **Midterm Exam** as the event name and **October 12** as the event date.

### 3. Review the results

The app shows the student every event it found before creating anything. The student can:

- correct an event name,
- correct a date,
- remove an event that is not a real deadline.

This matters because syllabi are written in many different styles, so a person should always get the last word.

### 4. Download the calendar

After review, the app generates a `.ics` file. That is the standard calendar-file format understood by Google Calendar, Apple Calendar, and Outlook.

When the student imports the file, the deadlines appear on their calendar as all-day events.

## The project’s main parts

```
Syllabus text or PDF
        |
        v
Flask web app
        |
        v
Parser finds possible events and dates
        |
        v
Student reviews and edits the events
        |
        v
Calendar maker creates an .ics file
        |
        v
Google / Apple / Outlook calendar
```

### The web app

The web app is the part users see in their browser. It shows the upload/paste form, displays clear error messages, presents the review page, and sends the final calendar file back as a download.

### The parser

The parser is the app’s "finder." Its job is to look through unstructured syllabus text and return a clean list of events. It does not deal with web pages or files; it only turns text into useful event information.

### The calendar maker

The calendar maker is the app’s "translator." It takes clean events from the parser and writes them in the official `.ics` calendar format.

### Tests

Tests are small automated checks that make sure the app still behaves correctly when it changes. They verify that supported date formats work, impossible dates are ignored, and the website can produce a valid calendar download.

## Important product rules

- The user chooses the academic start year.
- Dates from August through December belong to that start year.
- Dates from January through July belong to the following year.
- A scanned PDF with no selectable text cannot be read automatically; the user can paste its text instead.
- The user reviews results before download, so parser mistakes do not become calendar mistakes.

## A short explanation for a recruiter or interviewer

> SyllabusSync is a Flask web application that converts course syllabi into standard calendar files. It extracts deadline candidates from messy syllabus text, lets students review them, and exports the final events as an `.ics` file for Google Calendar, Apple Calendar, or Outlook. I separated the parsing, calendar-generation, and web-interface responsibilities so each part is easier to test and improve.

## What we will cover later

This document explains the product and the big-picture flow. When you are ready, we can make a separate code walkthrough that explains each file and important line in plain English.
