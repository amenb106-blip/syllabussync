from icalendar import Calendar, Event


def make_calendar(events):
    """Convert event dictionaries into iCalendar (.ics) bytes."""
    cal = Calendar()
    for event in events:
        ical_event = Event()
        ical_event.add("summary", event["name"])
        ical_event.add("dtstart", event["date"])
        cal.add_component(ical_event)
    return cal.to_ical()
