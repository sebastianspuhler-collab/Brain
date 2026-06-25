"""
Einmalige Gmail-Authentifizierung.
Ausführen: python3 _agent/gmail_setup.py

Voraussetzung: Gmail API im Google Cloud Projekt aktivieren
→ https://console.cloud.google.com → APIs & Dienste → Gmail API aktivieren
"""

import sys
from pathlib import Path

VAULT = Path.home() / "Documents" / "Prozessia-Brain"
sys.path.insert(0, str(VAULT / "_agent"))

from gmail_client import CREDS_PATH, TOKEN_PATH, SCOPES, get_service

def main():
    if not CREDS_PATH.exists():
        print(f"\nFEHLER: {CREDS_PATH} nicht gefunden.")
        print("→ drive_credentials.json aus Google Cloud Console herunterladen\n")
        sys.exit(1)

    # Token löschen um neue Scopes zu erzwingen
    if TOKEN_PATH.exists():
        TOKEN_PATH.unlink()
        print("Alter Token gelöscht, erzwinge Re-Login für Gmail-Scopes...")

    print("Browser öffnet sich für Google-Login (Gmail-Berechtigungen)...")
    svc = get_service()

    profile = svc.users().getProfile(userId="me").execute()
    email   = profile.get("emailAddress", "–")
    count   = profile.get("messagesTotal", 0)

    print(f"\n✓ Gmail verbunden!")
    print(f"  Adresse: {email}")
    print(f"  Nachrichten gesamt: {count:,}")
    print(f"  Token: {TOKEN_PATH}")
    print("\n→ Starte: bash _agent/start_brain_ui.sh\n")


if __name__ == "__main__":
    main()
