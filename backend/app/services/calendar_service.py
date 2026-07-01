"""Kalender-Übersicht: Outlook-Termine + Deadlines aus context.md.
Migriert aus brain_server.py:api_calendar()."""
import re
from datetime import datetime, timedelta

from app.config import get_settings
from app.services import cache
from app.services import outlook_client


def is_connected() -> bool:
    return outlook_client.is_authenticated()


def get_calendar_events() -> list[dict]:
    cached = cache.get("calendar")
    if cached is not None:
        return cached

    settings = get_settings()
    events: list[dict] = []

    if is_connected():
        try:
            raw = outlook_client.get_calendar_events(days=45)
            for e in raw:
                start_raw = e.get("start", {}).get("dateTime", "")
                end_raw = e.get("end", {}).get("dateTime", "")
                try:
                    start_dt = datetime.fromisoformat(start_raw[:19])
                    end_dt = datetime.fromisoformat(end_raw[:19])
                    if start_dt < datetime.now() - timedelta(hours=1):
                        continue
                    events.append({
                        "title": e.get("subject", ""),
                        "start": start_dt.strftime("%Y-%m-%dT%H:%M"),
                        "end": end_dt.strftime("%Y-%m-%dT%H:%M"),
                        "location": e.get("location", {}).get("displayName", ""),
                        "allDay": e.get("isAllDay", False),
                        "type": "meeting",
                    })
                except Exception:
                    pass
        except Exception:
            pass

    try:
        ctx = settings.context_path.read_text(encoding="utf-8")
        for line in ctx.splitlines():
            if "- [ ]" not in line and "DEADLINE" not in line.upper():
                continue
            for match in re.findall(r"\b(\d{1,2})\.(\d{1,2})\.?(?:\s*(\d{4}))?", line):
                day, month = int(match[0]), int(match[1])
                year = int(match[2]) if match[2] else datetime.now().year
                try:
                    dt = datetime(year, month, day)
                    if dt < datetime.now() - timedelta(days=1):
                        continue
                    # Nur das führende Checkbox-Präfix ("- [ ] " / "- [x] ") entfernen -
                    # ein reines Zeichen-Set wie [-\[\] x] würde auch Leerzeichen und
                    # den Buchstaben "x" aus dem restlichen Titeltext mitentfernen.
                    title = re.sub(r"^\s*-\s*\[[ xX]?\]\s*", "", line.split("(")[0]).strip()
                    events.append({
                        "title": title[:55],
                        "start": dt.strftime("%Y-%m-%dT00:00"),
                        "type": "deadline",
                        "allDay": True,
                    })
                except Exception:
                    pass
    except Exception:
        pass

    events.sort(key=lambda e: e.get("start", ""))
    seen: set[str] = set()
    unique = []
    for e in events:
        key = e["title"][:30]
        if key not in seen:
            seen.add(key)
            unique.append(e)

    result = unique[:12]
    cache.set("calendar", result)
    return result
