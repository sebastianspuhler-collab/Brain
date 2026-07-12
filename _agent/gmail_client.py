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
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

VAULT = Path(__file__).parent.parent
CREDS_PATH  = VAULT / "_agent" / "drive_credentials.json"
TOKEN_PATH  = VAULT / "_agent" / "gmail_token.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
]


def get_service():
    """Returns Gmail service or None if credentials are missing (e.g. on VPS)."""
    if not TOKEN_PATH.exists() and not CREDS_PATH.exists():
        return None
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif CREDS_PATH.exists():
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        else:
            return None
        TOKEN_PATH.write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def is_authenticated() -> bool:
    try:
        return get_service() is not None
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
        # Anhänge aus Payload extrahieren (kein Extra-API-Call nötig)
        atts = []
        def _scan_atts(parts):
            for p in parts:
                fname = p.get("filename", "")
                att_id = p.get("body", {}).get("attachmentId")
                if fname and att_id:
                    atts.append({
                        "attachmentId": att_id,
                        "filename": fname,
                        "mimeType": p.get("mimeType", "application/octet-stream"),
                        "size": p.get("body", {}).get("size", 0),
                    })
                _scan_atts(p.get("parts", []))
        _scan_atts(msg.get("payload", {}).get("parts", []))
        emails.append({
            "id":          msg["id"],
            "threadId":    msg["threadId"],
            "subject":     _header(msg, "Subject") or "(kein Betreff)",
            "from":        _header(msg, "From"),
            "to":          _header(msg, "To"),
            "date":        _header(msg, "Date"),
            "message_id":  _header(msg, "Message-ID"),
            "references":  _header(msg, "References"),
            "snippet":     msg.get("snippet", ""),
            "body":        body[:6000],
            "isRead":      "UNREAD" not in msg.get("labelIds", []),
            "attachments": atts,
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


def send_email_with_attachment(to, subject, body, attachment_path, cc=None):
    """Sendet eine Mail mit Datei-Anhang (z.B. Credential-Pakete)."""
    svc = get_service()
    msg = MIMEMultipart()
    msg["To"]      = to if isinstance(to, str) else ", ".join(to)
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc if isinstance(cc, str) else ", ".join(cc)
    msg.attach(MIMEText(body, "plain", "utf-8"))

    path = Path(attachment_path)
    part = MIMEBase("application", "octet-stream")
    part.set_payload(path.read_bytes())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{path.name}"')
    msg.attach(part)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    svc.users().messages().send(userId="me", body={"raw": raw}).execute()
    to_str = to if isinstance(to, str) else ", ".join(to)
    return f"Mail mit Anhang {path.name} gesendet an {to_str}"


def update_draft(draft_id, to, subject, body, cc=None):
    """Ersetzt Inhalt eines bestehenden Entwurfs (z.B. um nur den Betreff zu ändern)."""
    svc = get_service()
    msg = MIMEMultipart()
    msg["To"]      = to if isinstance(to, str) else ", ".join(to)
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc if isinstance(cc, str) else ", ".join(cc)
    msg.attach(MIMEText(body, "plain", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    svc.users().drafts().update(
        userId="me", id=draft_id, body={"message": {"raw": raw}}
    ).execute()
    return {"ok": True, "draft_id": draft_id}


def create_draft(to, subject, body, cc=None):
    """Legt einen Entwurf an, ohne ihn zu versenden."""
    svc = get_service()
    msg = MIMEMultipart()
    msg["To"]      = to if isinstance(to, str) else ", ".join(to)
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc if isinstance(cc, str) else ", ".join(cc)
    msg.attach(MIMEText(body, "plain", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft = svc.users().drafts().create(
        userId="me", body={"message": {"raw": raw}}
    ).execute()
    to_str = to if isinstance(to, str) else ", ".join(to)
    return {"ok": True, "draft_id": draft.get("id"), "to": to_str}


def search_emails_raw(query: str, max_results: int = 10) -> list:
    """Gmail-Suche mit nativer Query-Syntax (from:, to: etc.), gibt rohe Message-Metadaten zurück."""
    svc = get_service()
    resp = svc.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    results = []
    for m in resp.get("messages", []):
        msg = svc.users().messages().get(
            userId="me", id=m["id"], format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date"]
        ).execute()
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        results.append({
            "id": m["id"],
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "subject": headers.get("Subject", ""),
            "date": headers.get("Date", ""),
            "snippet": msg.get("snippet", ""),
        })
    return results


def reply_email(message_id, thread_id, to, orig_subject, orig_message_id,
                orig_references, body, cc=None):
    svc = get_service()
    msg = MIMEMultipart()
    msg["To"]         = to
    msg["Subject"]    = orig_subject if orig_subject.startswith("Re:") else f"Re: {orig_subject}"
    msg["In-Reply-To"] = orig_message_id
    msg["References"] = f"{orig_references} {orig_message_id}".strip()
    if cc:
        msg["Cc"] = cc if isinstance(cc, str) else ", ".join(cc)
    msg.attach(MIMEText(body, "plain", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    svc.users().messages().send(
        userId="me",
        body={"raw": raw, "threadId": thread_id}
    ).execute()
    return "Antwort gesendet."


def get_attachments(message_id: str) -> list:
    """Gibt alle Anhänge einer Mail zurück (ohne Inhalt, nur Metadaten)."""
    svc = get_service()
    msg = svc.users().messages().get(userId="me", id=message_id, format="full").execute()

    attachments = []

    def _scan_parts(parts):
        for part in parts:
            filename = part.get("filename", "")
            body = part.get("body", {})
            attachment_id = body.get("attachmentId")
            size = body.get("size", 0)
            mime = part.get("mimeType", "application/octet-stream")
            if filename and attachment_id:
                attachments.append({
                    "attachmentId": attachment_id,
                    "filename": filename,
                    "mimeType": mime,
                    "size": size,
                })
            sub = part.get("parts", [])
            if sub:
                _scan_parts(sub)

    payload = msg.get("payload", {})
    _scan_parts(payload.get("parts", []))
    # Manchmal ist der Anhang direkt im Payload (kein multipart)
    if not attachments and payload.get("body", {}).get("attachmentId"):
        attachments.append({
            "attachmentId": payload["body"]["attachmentId"],
            "filename": payload.get("filename", "anhang"),
            "mimeType": payload.get("mimeType", "application/octet-stream"),
            "size": payload["body"].get("size", 0),
        })
    return attachments


def download_attachment(message_id: str, attachment_id: str) -> bytes:
    """Lädt einen Anhang herunter und gibt die Rohdaten zurück."""
    svc = get_service()
    result = svc.users().messages().attachments().get(
        userId="me", messageId=message_id, id=attachment_id
    ).execute()
    data = result.get("data", "")
    if not data:
        return b""
    padded = data + "=" * (4 - len(data) % 4)
    return base64.urlsafe_b64decode(padded)
