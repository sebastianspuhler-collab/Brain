"""
Microsoft Graph API – Outlook Email & Kalender
Auth einmalig einrichten: python3 _agent/ms_login.py
Supports credentials aus .env (MS_CLIENT_ID, MS_TENANT_ID) oder ms_config.json
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import requests
import msal

VAULT = Path(__file__).parent.parent
CONFIG_PATH = VAULT / "_agent" / "ms_config.json"
TOKEN_CACHE_PATH = VAULT / "_agent" / "ms_token_cache.bin"
GRAPH = "https://graph.microsoft.com/v1.0"

SCOPES = [
    "https://graph.microsoft.com/Mail.ReadWrite",
    "https://graph.microsoft.com/Mail.Send",
    "https://graph.microsoft.com/Calendars.ReadWrite",
    "https://graph.microsoft.com/User.Read",
]


def _get_config() -> dict | None:
    """Versucht Microsoft Credentials zu laden von ENV oder Datei."""
    # 1. Prüfe ENV-Variablen
    client_id = os.getenv("MS_CLIENT_ID", "").strip()
    tenant_id = os.getenv("MS_TENANT_ID", "").strip()
    
    if client_id and tenant_id:
        return {"client_id": client_id, "tenant_id": tenant_id}
    
    # 2. Prüfe Datei
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except json.JSONDecodeError:
            print(f"WARNUNG: {CONFIG_PATH} ist kein gültiges JSON")
    
    return None


def _load_config():
    cfg = _get_config()
    if not cfg:
        raise FileNotFoundError(
            "Microsoft Credentials nicht gefunden.\n"
            "Optionen:\n"
            "  1. ENV-Variablen setzen: MS_CLIENT_ID, MS_TENANT_ID in .env\n"
            "  2. Datei erstellen: _agent/ms_config.json\n"
            "Siehe: _agent/ms_setup.md"
        )
    return cfg


def _get_app():
    cfg = _load_config()
    cache = msal.SerializableTokenCache()
    if TOKEN_CACHE_PATH.exists():
        cache.deserialize(TOKEN_CACHE_PATH.read_text())
    app = msal.PublicClientApplication(
        client_id=cfg["client_id"],
        authority=f"https://login.microsoftonline.com/{cfg['tenant_id']}",
        token_cache=cache,
    )
    return app, cache, cfg


def get_token():
    # Neues Format: direkte JSON-Antwort vom Device-Code-Flow
    if TOKEN_CACHE_PATH.exists():
        try:
            data = json.loads(TOKEN_CACHE_PATH.read_text())
            if "access_token" in data:
                # Token auf Ablauf prüfen
                import time
                expires_in = data.get("expires_in", 3600)
                cached_at = TOKEN_CACHE_PATH.stat().st_mtime
                if time.time() - cached_at < expires_in - 60:
                    return data["access_token"]
                # Refresh mit refresh_token
                if "refresh_token" in data:
                    cfg = _load_config()
                    r = requests.post(
                        f"https://login.microsoftonline.com/{cfg['tenant_id']}/oauth2/v2.0/token",
                        data={
                            "grant_type":    "refresh_token",
                            "client_id":     cfg["client_id"],
                            "refresh_token": data["refresh_token"],
                        }
                    )
                    result = r.json()
                    if "access_token" in result:
                        TOKEN_CACHE_PATH.write_text(json.dumps(result))
                        return result["access_token"]
        except Exception:
            pass
    # Fallback: MSAL-Cache
    try:
        app, cache, _ = _get_app()
        accounts = app.get_accounts()
        if accounts:
            result = app.acquire_token_silent(SCOPES, account=accounts[0])
            if result and "access_token" in result:
                return result["access_token"]
    except Exception:
        pass
    raise PermissionError("Nicht eingeloggt – bitte 'python3 _agent/ms_login_device.py' ausführen.")


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


# ── E-Mail ────────────────────────────────────────────────────────────────────

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


# ── Kalender ─────────────────────────────────────────────────────────────────

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
