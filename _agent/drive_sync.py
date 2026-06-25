"""
Google Drive Sync für Prozessia Second Brain
Lädt den WebWokrs Ordner in _inbox – überspringt Duplikate und Code-Dateien.
Beim ersten Start: Browser öffnet sich für Google-Login (einmalig).
"""

import os
import io
import json
from pathlib import Path
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

VAULT_PATH = Path.home() / "Documents" / "Prozessia-Brain"
INBOX_PATH = VAULT_PATH / "_inbox" / "drive_import"
DRIVE_CACHE_PATH = VAULT_PATH / "_agent" / "logs" / "drive_sync_cache.json"

def load_drive_cache():
    if DRIVE_CACHE_PATH.exists():
        try:
            return set(json.loads(DRIVE_CACHE_PATH.read_text()))
        except Exception:
            return set()
    return set()

def save_drive_cache(cache):
    DRIVE_CACHE_PATH.write_text(json.dumps(list(cache)))
CREDS_PATH = VAULT_PATH / "_agent" / "drive_token.json"
CLIENT_SECRETS = VAULT_PATH / "_agent" / "drive_credentials.json"

WEBWOKRS_FOLDER_ID = "1fCLfro7TtOsKKrI7GeMeSuAjNxm8mrvE"

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

SKIP_EXTENSIONS = {
    ".js", ".ts", ".map", ".mjs", ".jsx", ".tsx", ".css",
    ".yml", ".yaml", ".lock", ".editorconfig", ".orig",
    ".enc", ".lnk"
}

SKIP_NAMES = {
    "package.json", "package-lock.json", "tsconfig.json",
    "Thumbs.db", ".DS_Store"
}

SKIP_NAME_PREFIXES = (
    "README", "readme", "LICENSE", "license",
    "CHANGELOG", "HISTORY", "CONTRIBUTING"
)

GOOGLE_EXPORT_TYPES = {
    "application/vnd.google-apps.document":
        ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx"),
    "application/vnd.google-apps.spreadsheet":
        ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"),
    "application/vnd.google-apps.presentation":
        ("application/vnd.openxmlformats-officedocument.presentationml.presentation", ".pptx"),
    "application/vnd.google-apps.drawing":
        ("application/pdf", ".pdf"),
}

SKIP_MIME = {
    "application/vnd.google-apps.folder",
    "application/vnd.google-apps.shortcut",
    "video/mp4", "video/quicktime", "video/avi",
    "audio/mpeg", "audio/mp4",
}

downloaded = 0
skipped = 0
errors = 0


def get_service():
    creds = None
    if CREDS_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(CREDS_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CLIENT_SECRETS.exists():
                print(f"\nFEHLER: {CLIENT_SECRETS} nicht gefunden.")
                print("Anleitung: siehe drive_sync_setup.md\n")
                exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS), SCOPES)
            creds = flow.run_local_server(port=0)
        CREDS_PATH.write_text(creds.to_json())
    return build("drive", "v3", credentials=creds)


def should_skip(name, mime):
    if mime in SKIP_MIME:
        return True
    if name in SKIP_NAMES:
        return True
    if any(name.startswith(p) for p in SKIP_NAME_PREFIXES):
        return True
    ext = Path(name).suffix.lower()
    if ext in SKIP_EXTENSIONS:
        return True
    return False


def list_files(service, folder_id):
    files = []
    page_token = None
    while True:
        resp = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="nextPageToken, files(id, name, mimeType, size)",
            pageToken=page_token,
            pageSize=100
        ).execute()
        files.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return files


def download_file(service, file_id, name, mime, dest_folder, cache):
    global downloaded, skipped, errors
    if file_id in cache:
        skipped += 1
        return
    dest_folder.mkdir(parents=True, exist_ok=True)

    if mime in GOOGLE_EXPORT_TYPES:
        export_mime, ext = GOOGLE_EXPORT_TYPES[mime]
        out_name = Path(name).stem + ext
        dest = dest_folder / out_name
        request = service.files().export_media(fileId=file_id, mimeType=export_mime)
    else:
        dest = dest_folder / name
        request = service.files().get_media(fileId=file_id)

    try:
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        dest.write_bytes(buf.getvalue())
        print(f"  ✓ {name}")
        cache.add(file_id)
        save_drive_cache(cache)
        downloaded += 1
    except Exception as e:
        print(f"  ✗ {name}: {e}")
        errors += 1


def sync_folder(service, folder_id, dest_folder, cache, depth=0):
    files = list_files(service, folder_id)
    for f in files:
        name = f["name"]
        mime = f["mimeType"]

        if mime == "application/vnd.google-apps.folder":
            subfolder = dest_folder / name
            sync_folder(service, f["id"], subfolder, cache, depth + 1)
        elif should_skip(name, mime):
            pass
        else:
            download_file(service, f["id"], name, mime, dest_folder, cache)


def scan_folder_ids(service, folder_id, cache):
    """Nur IDs sammeln ohne Downloaden – für Cache-Initialisierung."""
    files = list_files(service, folder_id)
    for f in files:
        if f["mimeType"] == "application/vnd.google-apps.folder":
            scan_folder_ids(service, f["id"], cache)
        elif not should_skip(f["name"], f["mimeType"]):
            cache.add(f["id"])


def run(scan_only=False):
    global downloaded, skipped, errors
    INBOX_PATH.mkdir(parents=True, exist_ok=True)

    print("Google Drive Sync – WebWokrs → _inbox/drive_import")
    print("=" * 50)

    service = get_service()
    cache = load_drive_cache()
    print(f"Verbunden. {len(cache)} Dateien bereits im Cache.")

    if scan_only:
        print("Scan-Modus: Baue Cache auf ohne Download...\n")
        scan_folder_ids(service, WEBWOKRS_FOLDER_ID, cache)
        save_drive_cache(cache)
        print(f"Cache gespeichert: {len(cache)} Dateien markiert.")
        return

    print("Starte Sync...\n")
    sync_folder(service, WEBWOKRS_FOLDER_ID, INBOX_PATH, cache)

    print(f"\n{'=' * 50}")
    print(f"Fertig: {downloaded} heruntergeladen, {skipped} übersprungen, {errors} Fehler")
    print(f"Dateien in: {INBOX_PATH}")
    print("\nJetzt heartbeat ausführen:")
    print("  python3 _agent/heartbeat.py")


if __name__ == "__main__":
    import sys
    scan_only = "--scan" in sys.argv
    run(scan_only=scan_only)
