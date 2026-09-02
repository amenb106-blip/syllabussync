# SyllabusSync — UI Redesign Notes

Spec for implementing the redesigned UI. Scope: `static/style.css`, `templates/index.html`, `templates/review.html`, and optionally `message_page()` in `app.py`. No changes to routes, form field names, or Python logic — the redesign keeps the exact same forms and endpoints.

## Design system

**Fonts** (add a Google Fonts link in each template's `<head>`):
- Headings + logo wordmark: **Bricolage Grotesque** (weights 500/600/700), fallback Georgia, serif
- Body/UI: **Instrument Sans** (weights 400/500/600), fallback "Segoe UI", system-ui, sans-serif

```html
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@500;600;700&family=Instrument+Sans:wght@400;500;600&display=swap">
```

**Colors** (keep existing tokens, update these):
- Page background: `#f3f5f9` (was `#f5f7fa`)
- Accent stays `#2f6fed`, hover `#2456bd`, soft tint `#eaf1fe`
- Text `#14181f`, muted `#5b6472`, borders `#dfe3ea`, subtle row divider `#eef1f6`
- Placeholder text `#9aa3b2`
- Confidence chips unchanged: high `#0b6b3a` on `#e7f6ed`, low `#805200` on `#fff4d6`

**Shape & depth:**
- Cards: white, 1px `#dfe3ea` border, border-radius **16px**, shadow `0 8px 30px rgba(20,24,31,0.07)`
- Inputs/buttons: border-radius 10px (inputs 8px inside tables)
- Pills/chips: border-radius 999px

## Shared header (all pages)

Replace the plain `<h1>SyllabusSync</h1>` with a top bar, full width, padding `24px 64px`:
- Left: logo — a 36×36px `#2f6fed` rounded square (10px radius) containing a white stroke-SVG calendar-with-checkmark icon, next to the wordmark "SyllabusSync" (Bricolage Grotesque, 20px, weight 700).
- Right (home only): muted 14px text "Free · No account needed". On review page: a muted "Start over" link.

## Home page (index.html)

Two-column layout (CSS grid, 2 equal columns, 80px gap, max content width ~1310px, padding `56px 64px`):

**Left column** — the pitch:
- H1, 52px, Bricolage Grotesque 700, line-height 1.08: "Every deadline, straight to your calendar."
- Sub-paragraph, 18px muted: "Paste a syllabus or upload the PDF. SyllabusSync finds the exams, projects, and due dates — you approve them, your calendar remembers them."
- Three numbered steps (30px round `#eaf1fe` circles with `#2456bd` numbers, 14px gap): 1 "Add your syllabus", 2 "Review the dates it found", 3 "Download one file for your whole term".
- Footer line with small calendar icon: "Works with Google Calendar, Apple Calendar, and Outlook."

**Right column** — the form card (white card per design system, 32px padding):
- **Tab switcher** replacing the "or" divider: a segmented control (`#f3f5f9` track, 10px radius, 5px padding) with two tabs "Paste text" / "Upload PDF". Active tab: white background, 7px radius, small shadow, weight 600. Tabs toggle visibility of the textarea field vs. the file input field (a few lines of vanilla JS; both inputs stay in the same form so the backend is unchanged — the backend already prefers the PDF when present, so also clear the hidden input's value on switch).
- Syllabus textarea: 220px tall, placeholder with example lines ("Week 5 — Midterm Exam: October 14", "Project 1 due Sep 25", "Final Exam 12/16").
- Academic year field: label "Academic year starts in", ~160px wide, hint below: "Aug–Dec dates use this year; Jan–Jul use the next."
- Primary button, full width: search icon + "Find events" (15px vertical padding, 16px, weight 600).
- Centered muted caption below: "You'll review everything before anything is created."

## Review page (review.html)

Content column ~1080px centered. Keep all existing form fields, names, and the group-toggle JS.

- Header row: H1 "Review your events" (36px Bricolage Grotesque) with subtitle "Clear deadlines are already selected. Fix a name or date inline, and untick anything that doesn't belong." Right-aligned summary pill (`#eaf1fe` bg, `#2456bd` text, 999px radius): "{N} dates found · {M} selected" (M updates live via JS as checkboxes change).
- Each group becomes a white card (14px radius, overflow hidden):
  - Card header (padding `18px 24px`, bottom border): group name 17px/600 with a 13px muted subtitle line; "Include group" checkbox on the right.
  - Column header strip: `#f8fafd` bg, 12px uppercase 600 letter-spaced muted labels: (checkbox) / Event name / Date / Why it's here.
  - Rows as a grid `56px 1fr 190px 300px`, 16px gap, padding `12px 24px`, `#eef1f6` divider between rows. Name and date stay as inputs; the reason cell shows the confidence chip + muted 13px reason text.
- **Sticky bottom action bar**: fixed to viewport bottom, white, top border, shadow `0 -4px 20px rgba(20,24,31,0.06)`. Inside (same 1080px column): left "**{M} events** will be added to your calendar"; right: "Start over" link + primary button with download icon "Download calendar (.ics)". Give the page bottom padding so content isn't hidden behind the bar.

## Error pages (message_page in app.py, optional)

Centered white card (560px, 48px padding, centered text): a 64px round `#fff4d6` circle with an amber `#805200` document-alert SVG icon; heading 28px Bricolage Grotesque (e.g. "We couldn't read that PDF"); the existing message text as body copy in muted 16px; then two buttons side by side — primary "Paste the text instead" (link to `/`) and a bordered white secondary "Choose a different PDF" (also `/`). Keep the message text passed by each caller.

## General notes

- Icons are inline stroke SVGs (2px stroke, round caps), never emoji.
- Keep all `:focus-visible` styles and aria-labels from the current templates.
- Keep the mobile media query behavior: stack the home page to one column under ~900px; full-width buttons under 600px; the review grid can scroll horizontally on small screens.
