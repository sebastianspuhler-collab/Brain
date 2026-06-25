"""
Gmail API Client – Email lesen, senden, antworten
Auth einmalig: python3 _agent/gmail_setup.py
Nutzt dieselbe drive_credentials.json (selbes Google Cloud Projekt)
"""

import base64
import json
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

VAULT = Path.home() / "Documents" / "Prozessia-Brain"
CREDS_PATH  = VAULT / "_agent" / "drive_credentials.json"   # wiederverwendet
TOKEN_PATH  = VAULT / "_agent" / "gmail_token.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
]


def get_service():
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDS_PATH.exists():
                raise FileNotFoundError(
                    f"{CREDS_PATH} nicht gefunden. "
                    "Stelle sicher dass drive_credentials.json vorhanden ist "
                    "und Gmail API im Google Cloud Projekt aktiviert ist."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def is_authenticated():
    try:
        get_service()
        return True
    except Exception:
        return False


def _decode_part(data: str) -> str:
    if not data:
        return ""
    padded = data + "=" * (4 - len(data) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="ignore")


def _extract_body(payload: dict) -> str:
    """Extrahiert Plain-Text aus Gmail MIME-Payload."""
    mime = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data", "")

    if mime == "text/plain" and body_data:
        return _decode_part(body_data)
    if mime == "text/html" and body_data:
        return re.sub(r"<[^>]+>", " ", _decode_part(body_data)).strip()

    text_plain = ""
    text_html  = ""
    for part in payload.get("parts", []):
        sub = _extract_body(part)
        if part.get("mimeType") == "text/plain":
            text_plain = sub
        elif part.get("mimeType") == "text/html":
            text_html = sub
        elif not text_plain:
            text_plain = sub

    return text_plain or text_html


def _header(message, name):
    for h in message.get("payload", {}).get("headers", []):
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


# ── E-Mail lesen ──────────────────────────────────────────────────────────────

def get_emails(top=20, unread_only=False):
    svc = get_service()
    q = "is:unread" if unread_only else ""
    resp = svc.users().messages().list(
        userId="me", labelIds=["INBOX"], q=q, maxResults=top
    ).execute()

    ids = [m["id"] for m in resp.get("messages", [])]
    emails = []
    for mid in ids:
        msg = svc.users().messages().get(
            userId="me", id=mid, format="full"
        ).execute()
        body = _extract_body(msg.get("payload", {}))
        emails.append({
            "id":         msg["id"],
            "threadId":   msg["threadId"],
            "subject":    _header(msg, "Subject") or "(kein Betreff)",
            "from":       _header(msg, "From"),
            "to":         _header(msg, "To"),
            "date":       _header(msg, "Date"),
            "message_id": _header(msg, "Message-ID"),
            "references": _header(msg, "References"),
            "snippet":    msg.get("snippet", ""),
            "body":       body[:6000],
            "isRead":     "UNREAD" not in msg.get("labelIds", []),
        })
    return emails


def mark_as_read(message_id):
    svc = get_service()
    svc.users().messages().modify(
        userId="me", id=message_id,
        body={"removeLabelIds": ["UNREAD"]}
    ).execute()


def send_email(to, subject, body, cc=None):
    svc = get_service()
    msg = MIMEMultipart()
    msg["To"]      = to if isinstance(to, str) else ", ".join(to)
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc if isinstance(cc, str) else ", ".join(cc)
    msg.attach(MIMEText(body, "plain", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    svc.users().messages().send(userId="me", body={"raw": raw}).execute()
    to_str = to if isinstance(to, str) else ", ".join(to)
    return f"Mail gesendet an {to_str}"


def reply_email(message_id, thread_id, to, orig_subject, orig_message_id,
                orig_references, body):
    svc = get_service()
    msg = MIMEMultipart()
    msg["To"]         = to
    msg["Subject"]    = orig_subject if orig_subject.startswith("Re:") else f"Re: {orig_subject}"
    msg["In-Reply-To"] = orig_message_id
    msg["References"] = f"{orig_references} {orig_message_id}".strip()
    msg.attach(MIMEText(body, "plain", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    svc.users().messages().send(
        userId="me",
        body={"raw": raw, "threadId": thread_id}
    ).execute()
    return "Antwort gesendet."
