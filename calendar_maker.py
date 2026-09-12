from datetime import datetime, timezone, timedelta
from uuid import NAMESPACE_URL, uuid5

from icalendar import Calendar, Event, Alarm


def make_calendar(events, reminder_minutes=None):
    if reminder_minutes not in (None, 15, 60, 1440):
        raise ValueError("Invalid reminder interval")
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
        if reminder_minutes is not None:
            alarm = Alarm()
            alarm.add("action", "DISPLAY")
            alarm.add("description", event["name"])
            alarm.add("trigger", -timedelta(minutes=reminder_minutes))
            ical_event.add_component(alarm)
        cal.add_component(ical_event)
    return cal.to_ical()
