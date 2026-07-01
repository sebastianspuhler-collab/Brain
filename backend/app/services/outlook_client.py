"""Microsoft Graph API - Outlook Email & Kalender.
Migriert aus _agent/outlook_client.py, unverändert bis auf den VAULT-Pfad.
Auth einmalig einrichten: siehe _agent/ms_login.py / ms_login_device.py.
"""
import json
import time
from datetime import datetime, timedelta

import msal
import requests

from app.config import get_settings

GRAPH = "https://graph.microsoft.com/v1.0"

SCOPES = [
    "https://graph.microsoft.com/Mail.ReadWrite",
    "https://graph.microsoft.com/Mail.Send",
    "https://graph.microsoft.com/Calendars.ReadWrite",
    "https://graph.microsoft.com/User.Read",
]


def _config_path():
    return get_settings().agent_dir / "ms_config.json"


def _token_cache_path():
    return get_settings().agent_dir / "ms_token_cache.bin"


def _load_config():
    path = _config_path()
    if not path.exists():
        raise FileNotFoundError("ms_config.json fehlt - siehe _agent/ms_setup.md")
    return json.loads(path.read_text())


def _get_app():
    cfg = _load_config()
    cache = msal.SerializableTokenCache()
    token_cache_path = _token_cache_path()
    if token_cache_path.exists():
        cache.deserialize(token_cache_path.read_text())
    app = msal.PublicClientApplication(
        client_id=cfg["client_id"],
        authority=f"https://login.microsoftonline.com/{cfg['tenant_id']}",
        token_cache=cache,
    )
    return app, cache, cfg


def get_token():
    token_cache_path = _token_cache_path()
    if token_cache_path.exists():
        try:
            data = json.loads(token_cache_path.read_text())
            if "access_token" in data:
                expires_in = data.get("expires_in", 3600)
                cached_at = token_cache_path.stat().st_mtime
                if time.time() - cached_at < expires_in - 60:
                    return data["access_token"]
                if "refresh_token" in data:
                    cfg = _load_config()
                    r = requests.post(
                        f"https://login.microsoftonline.com/{cfg['tenant_id']}/oauth2/v2.0/token",
                        data={
                            "grant_type": "refresh_token",
                            "client_id": cfg["client_id"],
                            "refresh_token": data["refresh_token"],
                        },
                    )
                    result = r.json()
                    if "access_token" in result:
                        token_cache_path.write_text(json.dumps(result))
                        return result["access_token"]
        except Exception:
            pass
    try:
        app, cache, _ = _get_app()
        accounts = app.get_accounts()
        if accounts:
            result = app.acquire_token_silent(SCOPES, account=accounts[0])
            if result and "access_token" in result:
                return result["access_token"]
    except Exception:
        pass
    raise PermissionError("Nicht eingeloggt - bitte 'python3 _agent/ms_login_device.py' ausführen.")


def is_authenticated():
    try:
        get_token()
        return True
    except Exception:
        return False


def _headers():
    return {"Authorization": f"Bearer {get_token()}", "Content-Type": "application/json"}


def _get(url, params=None):
    r = requests.get(url, headers=_headers(), params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def _post(url, data):
    r = requests.post(url, headers=_headers(), json=data, timeout=15)
    r.raise_for_status()
    return r.json() if r.content else {}


def _patch(url, data):
    requests.patch(url, headers=_headers(), json=data, timeout=10)


def get_emails(folder="inbox", top=20, unread_only=False):
    params = {
        "$top": top,
        "$orderby": "receivedDateTime desc",
        "$select": "id,subject,from,toRecipients,receivedDateTime,isRead,bodyPreview,body",
    }
    if unread_only:
        params["$filter"] = "isRead eq false"
    return _get(f"{GRAPH}/me/mailFolders/{folder}/messages", params).get("value", [])


def send_email(to, subject, body, cc=None):
    to_list = [to] if isinstance(to, str) else to
    msg = {
        "message": {
            "subject": subject,
            "body": {"contentType": "Text", "content": body},
            "toRecipients": [{"emailAddress": {"address": a.strip()}} for a in to_list],
        },
        "saveToSentItems": True,
    }
    if cc:
        cc_list = [cc] if isinstance(cc, str) else cc
        msg["message"]["ccRecipients"] = [{"emailAddress": {"address": a.strip()}} for a in cc_list]
    _post(f"{GRAPH}/me/sendMail", msg)
    return f"Mail gesendet an {', '.join(to_list)}"


def reply_email(message_id, body, reply_all=False):
    ep = "replyAll" if reply_all else "reply"
    _post(f"{GRAPH}/me/messages/{message_id}/{ep}", {"comment": body})
    return "Antwort gesendet."


def mark_as_read(message_id):
    _patch(f"{GRAPH}/me/messages/{message_id}", {"isRead": True})


def get_calendar_events(days=7):
    now = datetime.utcnow()
    end = now + timedelta(days=days)
    params = {
        "startDateTime": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "endDateTime": end.strftime("%Y-%m-%dT%H:%M:%S"),
        "$orderby": "start/dateTime",
        "$select": "id,subject,start,end,location,bodyPreview,attendees,isAllDay,organizer",
        "$top": 50,
    }
    headers = _headers()
    headers["Prefer"] = 'outlook.timezone="Europe/Berlin"'
    r = requests.get(f"{GRAPH}/me/calendarView", headers=headers, params=params, timeout=15)
    r.raise_for_status()
    return r.json().get("value", [])


def create_calendar_event(subject, start_dt, end_dt, body="", attendees=None, location=""):
    if isinstance(start_dt, datetime):
        start_dt = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
    if isinstance(end_dt, datetime):
        end_dt = end_dt.strftime("%Y-%m-%dT%H:%M:%S")
    event = {
        "subject": subject,
        "body": {"contentType": "Text", "content": body},
        "start": {"dateTime": start_dt, "timeZone": "Europe/Berlin"},
        "end": {"dateTime": end_dt, "timeZone": "Europe/Berlin"},
    }
    if location:
        event["location"] = {"displayName": location}
    if attendees:
        att_list = [attendees] if isinstance(attendees, str) else attendees
        event["attendees"] = [
            {"emailAddress": {"address": a.strip()}, "type": "required"} for a in att_list
        ]
    _post(f"{GRAPH}/me/events", event)
    return f"Termin erstellt: '{subject}' am {start_dt[:10]}"
