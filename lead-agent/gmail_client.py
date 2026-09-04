"""Gmail-Entwürfe für Outreach-Mails - eigenständige Kopie des
Ausschnitts von backend/app/services/gmail_client.py, den der Lead-Agent
tatsächlich braucht (nur create_draft, kein Lesen/Antworten/Anhänge - dafür
gibt es keinen Anwendungsfall hier). Kein Shared-Import über den
Container-Rand (gleiche Begründung wie überall in diesem Modul).

WICHTIG: nutzt DENSELBEN OAuth-Token wie das Hauptbackend
(_agent/gmail_token.json im Vault-Mount) statt einer eigenen Google-Consent-
Anmeldung - der Lead-Agent hat wegen vault_leads.py ohnehin
Lese-/Schreibzugriff auf den ganzen Vault (siehe docker-compose.yml,
${VAULT_PATH}:/vault). Läuft der Token ab und es existiert kein
Refresh-Token mehr, schlägt create_draft() mit einer klaren Fehlermeldung
fehl statt eine interaktive Consent-Flow zu versuchen (kein Browser im
Container) - dann muss der Token einmal über das Hauptbackend erneuert
werden (dort läuft der interaktive Flow bereits, siehe
backend/app/services/gmail_client.py::get_service())."""
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config import get_settings

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
]


def _token_path():
    return get_settings().vault_path / "_agent" / "gmail_token.json"


def is_authenticated() -> bool:
    return _token_path().exists()


def get_service():
    token_path = _token_path()
    if not token_path.exists():
        raise RuntimeError(
            "Gmail nicht verbunden: _agent/gmail_token.json fehlt im Vault. "
            "Einmal über das Hauptbackend authentifizieren (dort läuft der "
            "interaktive OAuth-Flow), der Lead-Agent nutzt danach denselben Token."
        )
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_path.write_text(creds.to_json())
        else:
            raise RuntimeError("Gmail-Token abgelaufen und kein Refresh-Token vorhanden - im Hauptbackend neu authentifizieren.")
    return build("gmail", "v1", credentials=creds)


def create_draft(to: str, subject: str, body: str, cc: str | None = None) -> dict:
    """Legt einen Gmail-Entwurf an (users.drafts.create) - NIE ein Senden.
    Bewusst OHNE automatische Signatur (anders als das Hauptbackend-Pendant):
    der Lead-Agent kennt Sebastians echte Signatur nicht und soll sie nicht
    erraten - der Nutzer ergänzt sie beim Gegenlesen im Entwurf selbst."""
    svc = get_service()
    msg = MIMEMultipart()
    msg["To"] = to
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc
    msg.attach(MIMEText(body, "plain", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft = svc.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
    return {"draft_id": draft.get("id"), "message": f"Entwurf an {to} angelegt (nicht gesendet)"}
