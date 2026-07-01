"""Gmail-Übersicht fürs Dashboard. Migriert aus brain_server.py:api_gmail()."""
import re
from datetime import datetime
from email.utils import parsedate_to_datetime

from app.services import cache
from app.services import gmail_client

CACHE_TTL_MAIL = 60


def is_connected() -> bool:
    return gmail_client.is_authenticated()


def get_gmail_summary() -> list[dict]:
    cached = cache.get("gmail", ttl=CACHE_TTL_MAIL)
    if cached is not None:
        return cached
    if not is_connected():
        return []
    try:
        raw = gmail_client.get_emails(top=50)
    except Exception:
        return []

    result = []
    for e in raw:
        sender = e.get("from", "")
        m = re.match(r'"?([^"<]+)"?\s*<?([^>]*)>?', sender)
        name = m.group(1).strip().strip('"') if m else sender[:40]
        addr = m.group(2).strip() if m else sender

        date_str = e.get("date", "")
        try:
            dt = parsedate_to_datetime(date_str)
            now_tz = datetime.now(dt.tzinfo)
            delta = now_tz - dt
            if delta.days == 0:
                time_label = dt.strftime("%H:%M")
            elif delta.days == 1:
                time_label = "Gestern"
            else:
                time_label = dt.strftime("%d.%m.")
        except Exception:
            time_label = date_str[:10]

        snippet = e.get("snippet", "") or e.get("body", "")
        snippet = re.sub(r"\s+", " ", snippet).strip()[:200]

        result.append({
            "id": e.get("id", ""),
            "from": name,
            "email": addr,
            "subject": e.get("subject", "(kein Betreff)"),
            "snippet": snippet,
            "time": time_label,
            "unread": not e.get("isRead", True),
        })
    cache.set("gmail", result)
    return result
