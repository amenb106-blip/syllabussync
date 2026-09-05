from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid5

from icalendar import Calendar, Event


def make_calendar(events):
    cal = Calendar()
    cal.add("version", "2.0")
    cal.add("prodid", "-//SyllabusSync//Syllabus Calendar//EN")
    timestamp = datetime.now(timezone.utc)
    for event in events:
        ical_event = Event()
        start = (
            event["date"]
            if event.get("time") is None
            else datetime.combine(event["date"], event["time"])
        )
        identity = f"syllabussync:event:{start.isoformat()}:{event['name']}"
        ical_event.add("uid", str(uuid5(NAMESPACE_URL, identity)))
        ical_event.add("dtstamp", timestamp)
        ical_event.add("summary", event["name"])
        ical_event.add("dtstart", start)
        cal.add_component(ical_event)
    return cal.to_ical()
