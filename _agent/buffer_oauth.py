#!/usr/bin/env python3
"""
buffer_oauth.py — Einmaliger OAuth2-Flow um einen gültigen Buffer Access Token zu holen.

Usage:
  python3 _agent/buffer_oauth.py

Voraussetzung:
  - Buffer Developer App unter https://buffer.com/developers/apps angelegt
  - Redirect URI in der App auf http://localhost:8765/callback gesetzt
"""

import webbrowser
import urllib.parse
import requests
import sys
from pathlib import Path

ENV_PATH = Path.home() / "Documents" / "Prozessia-Brain" / "_inbox" / "Branding" / "claude-linkedin-auto-poster" / ".env"
REDIRECT_URI = "https://localhost:8765/callback"
AUTH_URL = "https://bufferapp.com/oauth2/authorize"
TOKEN_URL = "https://api.bufferapp.com/1/oauth2/token.json"


def update_env(token: str):
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
        new_lines = []
        replaced = False
        for line in lines:
            if line.startswith("BUFFER_API_TOKEN="):
                new_lines.append(f"BUFFER_API_TOKEN={token}")
                replaced = True
            else:
                new_lines.append(line)
        if not replaced:
            new_lines.append(f"BUFFER_API_TOKEN={token}")
        ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    else:
        ENV_PATH.write_text(f"BUFFER_API_TOKEN={token}\n", encoding="utf-8")


def run():
    print("=== Buffer OAuth2 Setup ===\n")
    client_id = input("Client ID: ").strip()

    if not client_id:
        print("FEHLER: Client ID erforderlich.")
        sys.exit(1)

    client_secret = ""

    # Open browser
    auth_params = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
    })
    url = f"{AUTH_URL}?{auth_params}"
    print(f"\nÖffne Browser für Buffer-Autorisierung...")
    webbrowser.open(url)
    print("\nNach der Autorisierung leitet Buffer auf eine Fehlerseite weiter — das ist normal.")
    print("Kopiere aus der URL-Leiste den Wert nach '?code=' und füge ihn hier ein:\n")

    received_code = input("Code: ").strip()
    if not received_code:
        print("FEHLER: Kein Code eingegeben.")
        sys.exit(1)

    print(f"Code erhalten. Tausche gegen Access Token...")

    payload = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "code": received_code,
        "grant_type": "authorization_code",
    }
    if client_secret:
        payload["client_secret"] = client_secret

    resp = requests.post(TOKEN_URL, data=payload, timeout=15)

    body = resp.json()
    token = body.get("access_token")

    if not token:
        print(f"FEHLER: Token-Austausch fehlgeschlagen: {body}")
        sys.exit(1)

    update_env(token)
    print(f"\nErfolgreich! Access Token in .env gespeichert.")
    print(f"Token: {token[:12]}…")
    print(f"\nJetzt testen:")
    print(f"  python3 ~/Documents/Prozessia-Brain/_agent/buffer_push.py")


if __name__ == "__main__":
    run()
