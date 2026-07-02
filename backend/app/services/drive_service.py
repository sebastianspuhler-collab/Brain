"""Google Drive: Kundenordner-Struktur anlegen + Dateien hochladen.
Nutzt einen Service Account (kein interaktiver OAuth-Flow nötig, läuft
unbeaufsichtigt auf dem Server)."""
import io
import json

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account

from app.config import get_settings

SCOPES = ["https://www.googleapis.com/auth/drive"]

# Ordnerstruktur pro Kunde. Unterordner werden nach dem jeweiligen Elternordner
# angelegt (Reihenfolge der Liste = Verschachtelungstiefe).
FOLDER_STRUCTURE = {
    "00_Verträge": [],
    "01_Onboarding": ["Technische_Daten", "Kundendokumente"],
    "02_Projektdokumentation": ["Anforderungen", "Architektur", "Änderungsanfragen"],
    "03_Kommunikation": ["Meeting_Protokolle", "E-Mails"],
    "04_Lieferung": ["Releases", "Deployment", "Übergabeprotokolle"],
    "05_Abrechnung": ["Rechnungen", "Angebote"],
}


def _get_service():
    settings = get_settings()
    info = json.loads(settings.google_service_account_json)
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def _create_folder(service, name: str, parent_id: str) -> str:
    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]


def create_customer_folder_structure(kundenname: str) -> dict:
    """Legt die komplette Ordnerstruktur für einen neuen Kunden an.

    Gibt {"root_id": ..., "root_link": ..., "folders": {"01_Onboarding/Kundendokumente": id, ...}} zurück.
    """
    settings = get_settings()
    service = _get_service()

    root_id = _create_folder(service, kundenname, settings.drive_kunden_folder_id)
    folders = {}

    for top_name, children in FOLDER_STRUCTURE.items():
        top_id = _create_folder(service, top_name, root_id)
        folders[top_name] = top_id
        for child_name in children:
            child_id = _create_folder(service, child_name, top_id)
            folders[f"{top_name}/{child_name}"] = child_id

    return {
        "root_id": root_id,
        "root_link": f"https://drive.google.com/drive/folders/{root_id}",
        "folders": folders,
    }


def upload_file(folder_id: str, filename: str, content: bytes, mime_type: str = "application/octet-stream") -> str:
    """Lädt eine Datei in den angegebenen Ordner hoch, gibt den Web-Link zurück."""
    service = _get_service()
    media = MediaIoBaseUpload(io.BytesIO(content), mimetype=mime_type, resumable=False)
    metadata = {"name": filename, "parents": [folder_id]}
    file = service.files().create(body=metadata, media_body=media, fields="id, webViewLink").execute()
    return file.get("webViewLink", f"https://drive.google.com/file/d/{file['id']}")
