"""
Einmalige Microsoft-Authentifizierung für Outlook-Integration.
Ausführen: python3 _agent/ms_login.py
"""

import json
import sys
from pathlib import Path
import msal

VAULT = Path.home() / "Documents" / "Prozessia-Brain"
CONFIG_PATH = VAULT / "_agent" / "ms_config.json"
TOKEN_CACHE_PATH = VAULT / "_agent" / "ms_token_cache.bin"

SCOPES = [
    "https://graph.microsoft.com/Mail.ReadWrite",
    "https://graph.microsoft.com/Mail.Send",
    "https://graph.microsoft.com/Calendars.ReadWrite",
    "https://graph.microsoft.com/User.Read",
]


def main():
    if not CONFIG_PATH.exists():
        print(f"\nFEHLER: {CONFIG_PATH} nicht gefunden.")
        print("→ Erstelle die Datei gemäß _agent/ms_setup.md\n")
        sys.exit(1)

    cfg = json.loads(CONFIG_PATH.read_text())
    if not cfg.get("client_id") or cfg["client_id"] == "DEINE_CLIENT_ID":
        print("\nFEHLER: ms_config.json enthält noch Platzhalter.")
        print("→ Trage Client ID und Tenant ID ein (siehe _agent/ms_setup.md)\n")
        sys.exit(1)

    cache = msal.SerializableTokenCache()
    if TOKEN_CACHE_PATH.exists():
        cache.deserialize(TOKEN_CACHE_PATH.read_text())

    app = msal.PublicClientApplication(
        client_id=cfg["client_id"],
        authority=f"https://login.microsoftonline.com/{cfg['tenant_id']}",
        token_cache=cache,
    )

    # Silent login falls Token noch gültig
    accounts = app.get_accounts()
    result = None
    if accounts:
        print(f"Versuche Silent Login für {accounts[0]['username']}...")
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            print(f"\n✓ Bereits angemeldet als {accounts[0]['username']}")
            print("Token ist noch gültig, kein Re-Login nötig.")
            return

    print("\nBrowser öffnet sich für Microsoft-Login...")
    print("(Falls kein Browser aufgeht: Prüfe ms_setup.md für Device-Code-Flow)\n")
    result = app.acquire_token_interactive(scopes=SCOPES)

    if "access_token" not in result:
        print(f"\nFEHLER: {result.get('error_description', 'Login fehlgeschlagen')}")
        sys.exit(1)

    if cache.has_state_changed:
        TOKEN_CACHE_PATH.write_text(cache.serialize())

    import requests
    me = requests.get(
        "https://graph.microsoft.com/v1.0/me",
        headers={"Authorization": f"Bearer {result['access_token']}"}
    ).json()

    print(f"\n✓ Erfolgreich angemeldet!")
    print(f"  Name:  {me.get('displayName', '–')}")
    print(f"  Email: {me.get('mail') or me.get('userPrincipalName', '–')}")
    print(f"  Token: {TOKEN_CACHE_PATH}")
    print("\n→ Starte jetzt: bash _agent/start_brain_ui.sh\n")


if __name__ == "__main__":
    main()
