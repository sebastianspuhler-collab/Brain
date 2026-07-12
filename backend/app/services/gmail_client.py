"""Gmail API Client - Email lesen, senden, antworten.
Migriert aus _agent/gmail_client.py, unverändert bis auf den VAULT-Pfad (jetzt
aus zentralen Settings statt hartcodiert). Auth einmalig: siehe _agent/gmail_setup.py.
"""
import base64
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.config import get_settings

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
]


def _creds_path():
    return get_settings().agent_dir / "drive_credentials.json"


def _token_path():
    return get_settings().agent_dir / "gmail_token.json"


def get_service():
    """Returns Gmail service or None if credentials are missing (e.g. on VPS without tokens)."""
    creds_path = _creds_path()
    token_path = _token_path()
    if not token_path.exists() and not creds_path.exists():
        return None
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif creds_path.exists():
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)
        else:
            return None
        token_path.write_text(creds.to_json())
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
    text_html = ""
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


def get_emails(top=20, unread_only=False):
    svc = get_service()
    q = "is:unread" if unread_only else ""
    resp = svc.users().messages().list(
        userId="me", labelIds=["INBOX"], q=q, maxResults=top
    ).execute()

    ids = [m["id"] for m in resp.get("messages", [])]
    emails = []
    for mid in ids:
        msg = svc.users().messages().get(userId="me", id=mid, format="full").execute()
        body = _extract_body(msg.get("payload", {}))
        emails.append({
            "id": msg["id"],
            "threadId": msg["threadId"],
            "subject": _header(msg, "Subject") or "(kein Betreff)",
            "from": _header(msg, "From"),
            "to": _header(msg, "To"),
            "date": _header(msg, "Date"),
            "message_id": _header(msg, "Message-ID"),
            "references": _header(msg, "References"),
            "snippet": msg.get("snippet", ""),
            "body": body[:6000],
            "isRead": "UNREAD" not in msg.get("labelIds", []),
        })
    return emails


def mark_as_read(message_id):
    svc = get_service()
    svc.users().messages().modify(
        userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}
    ).execute()


def send_email(to, subject, body, cc=None):
    svc = get_service()
    msg = MIMEMultipart()
    msg["To"] = to if isinstance(to, str) else ", ".join(to)
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc if isinstance(cc, str) else ", ".join(cc)
    msg.attach(MIMEText(body, "plain", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    svc.users().messages().send(userId="me", body={"raw": raw}).execute()
    to_str = to if isinstance(to, str) else ", ".join(to)
    return f"Mail gesendet an {to_str}"


def reply_email(message_id, thread_id, to, orig_subject, orig_message_id, orig_references, body):
    svc = get_service()
    msg = MIMEMultipart()
    msg["To"] = to
    msg["Subject"] = orig_subject if orig_subject.startswith("Re:") else f"Re: {orig_subject}"
    msg["In-Reply-To"] = orig_message_id
    msg["References"] = f"{orig_references} {orig_message_id}".strip()
    msg.attach(MIMEText(body, "plain", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    svc.users().messages().send(userId="me", body={"raw": raw, "threadId": thread_id}).execute()
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
