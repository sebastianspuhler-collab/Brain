"""Aufgabenliste aus context.md. Migriert aus brain_server.py:api_tasks()."""
import re
from datetime import datetime

from app.config import get_settings


def get_tasks() -> list[dict]:
    settings = get_settings()
    try:
        ctx = settings.context_path.read_text(encoding="utf-8")
    except Exception:
        return []

    tasks = []
    for line in ctx.splitlines():
        if "- [ ]" in line:
            text = line.replace("- [ ]", "").strip()
            urgency = "normal"
            m = re.search(r"(\d{1,2})\.(\d{1,2})\.", text)
            if m:
                try:
                    day, month = int(m.group(1)), int(m.group(2))
                    dt = datetime(datetime.now().year, month, day)
                    days_left = (dt - datetime.now()).days
                    if days_left <= 7:
                        urgency = "urgent"
                    elif days_left <= 21:
                        urgency = "soon"
                except Exception:
                    pass
            tasks.append({"text": text, "urgency": urgency})
        elif "- [x]" in line or "- [X]" in line:
            text = line.replace("- [x]", "").replace("- [X]", "").strip()
            tasks.append({"text": text, "urgency": "done", "done": True})
    return tasks
