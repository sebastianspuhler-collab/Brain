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
# NICHT erweitern ohne den bestehenden Token neu auszustellen: Google prüft
# bei jedem Token-REFRESH den angefragten Scope gegen das, was der
# Refresh-Token beim ursprünglichen Consent bekommen hat. Live beobachtet
# (2026-08-11): SCOPES kurzzeitig um gmail.settings.basic erweitert, der
# nächste Refresh riss darauf sofort JEDEN Gmail-Zugriff ab ("invalid_scope"),
# nicht nur den neuen Signatur-Zugriff unten. get_signature() braucht diese
# Erweiterung am Ende ohnehin nicht (siehe dort) - SCOPES bewusst unverändert
# gelassen.


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


def send_email(to, subject, body, cc=None, include_signature: bool = True):
    svc = get_service()
    msg = _build_message(to, subject, body, cc=cc, include_signature=include_signature)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    svc.users().messages().send(userId="me", body={"raw": raw}).execute()
    to_str = to if isinstance(to, str) else ", ".join(to)
    return f"Mail gesendet an {to_str}"


_signature_cache: dict = {"html": None, "loaded": False}


def get_signature() -> str | None:
    """Liest die in Gmail hinterlegte Signatur des primären Send-As-Alias
    (users().settings().sendAs()) - das ist die einzige Quelle, die die exakte,
    von Sebastian selbst in Gmail gepflegte Signatur liefert, statt eine im
    Code nachgetippte Kopie zu riskieren, die bei der nächsten Änderung in
    Gmail veraltet.

    Offiziell verlangt Google dafür den Scope gmail.settings.basic - live
    getestet (2026-08-11) funktioniert der Read-Zugriff über sendAs().list()
    aber bereits mit dem vorhandenen gmail.modify-Token, per Tokeninfo-
    Introspection bestätigt (Token trägt nachweislich nur modify+compose).
    Kein Re-Login nötig. Falls Google das künftig strenger durchsetzt, bricht
    dieser Aufruf mit einer Exception ab - komplett abgefangen unten, dann
    liefert die Funktion sauber None statt die Mail-Erstellung zu crashen.
    Pro Prozesslauf einmal gecacht (Signatur ändert sich nicht mitten im
    Betrieb) - erspart einen API-Roundtrip bei jedem Entwurf."""
    if _signature_cache["loaded"]:
        return _signature_cache["html"]
    _signature_cache["loaded"] = True
    try:
        svc = get_service()
        if svc is None:
            return None
        result = svc.users().settings().sendAs().list(userId="me").execute()
        for alias in result.get("sendAs", []):
            if alias.get("isPrimary") or alias.get("isDefault"):
                sig = alias.get("signature") or None
                _signature_cache["html"] = sig
                return sig
        # Kein als primär markierter Alias gefunden - ersten mit Signatur nehmen.
        for alias in result.get("sendAs", []):
            if alias.get("signature"):
                _signature_cache["html"] = alias["signature"]
                return alias["signature"]
    except Exception:
        pass
    return None


def _text_to_html(text: str) -> str:
    import html as _html
    return _html.escape(text).replace("\n", "<br>\n")


def _build_message(to, subject, body, cc=None, include_signature: bool = True):
    """Baut die MIME-Nachricht für create_draft/send_email/reply_email.

    Mit Signatur wird die Mail multipart/alternative (Text- UND HTML-Teil):
    Gmail-Signaturen sind HTML (Links, Formatierung), ein reiner Text-Teil
    könnte das nicht abbilden. Ohne verfügbare Signatur (Scope fehlt noch,
    siehe get_signature()) bleibt es wie bisher ein einfacher Text-Teil."""
    signature = get_signature() if include_signature else None

    msg = MIMEMultipart("alternative") if signature else MIMEMultipart()
    msg["To"] = to if isinstance(to, str) else ", ".join(to)
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc if isinstance(cc, str) else ", ".join(cc)

    if signature:
        plain_sig = re.sub(r"<[^>]+>", "", signature).strip()
        msg.attach(MIMEText(f"{body}\n\n--\n{plain_sig}", "plain", "utf-8"))
        html_body = f"{_text_to_html(body)}<br><br>{signature}"
        msg.attach(MIMEText(html_body, "html", "utf-8"))
    else:
        msg.attach(MIMEText(body, "plain", "utf-8"))
    return msg


def create_draft(to, subject, body, cc=None, include_signature: bool = True):
    """Legt einen Gmail-Entwurf an (users.drafts.create), statt die Mail direkt
    zu senden - Gegenstück zu send_email(), gleicher MIME-Aufbau.

    Ergänzt 2026-08-11: der gmail.compose-Scope steht in SCOPES bereits seit
    Auth-Einrichtung, und _agent/gmail_token.json hat ihn auch tatsächlich
    gewährt bekommen (per Introspection auf dem Token-File geprüft) - das
    Fehlen dieser Funktion war ein reiner Code-Lücke, keine fehlende
    Berechtigung. Der Chat hat deshalb wiederholt (u.a. 2026-06-27 beim
    Mundinger-Fall) fälschlich "kein Schreibzugriff" gemeldet, obwohl der
    Zugriff die ganze Zeit vorhanden war.

    include_signature hängt automatisch Sebastians echte Gmail-Signatur an
    (siehe get_signature()) - abschaltbar für Antworten in laufenden Threads,
    wo Gmail selbst schon eine Signatur ergänzt."""
    svc = get_service()
    msg = _build_message(to, subject, body, cc=cc, include_signature=include_signature)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft = svc.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
    to_str = to if isinstance(to, str) else ", ".join(to)
    return {"draft_id": draft.get("id"), "message": f"Entwurf an {to_str} angelegt"}


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
