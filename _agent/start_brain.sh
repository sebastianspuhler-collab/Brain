#!/bin/bash
# Startet das aktuelle FastAPI-Backend (backend/app/main.py).
#
# Aktualisiert 2026-07-17: das alte Skript startete noch _agent/brain_server.py
# (die Pre-FastAPI-Architektur von vor der Backend-Migration) - selbst mit
# funktionierender launchd-Berechtigung wäre das der falsche Prozess gewesen.
# Zusätzlich lief dieser Dienst monatelang gegen eine macOS-Berechtigungssperre
# ("Operation not permitted" beim Ordnerzugriff aus dem headless launchd-Kontext) -
# dafür braucht der aufrufende Prozess "Vollständigen Festplattenzugriff" unter
# Systemeinstellungen -> Datenschutz & Sicherheit.

# Warte kurz bis Desktop geladen
sleep 5

VAULT_DIR="/Users/sesp01-user/vault/Prozessia-Brain"
BACKEND_DIR="$VAULT_DIR/backend"
cd "$BACKEND_DIR" || exit 1

# Sanity-Check: backend/.env muss existieren und einen Anthropic-Key haben -
# pydantic-settings liest .env selbst ein (kein manuelles Sourcing mehr nötig,
# solange uvicorn mit backend/ als Arbeitsverzeichnis läuft), aber ohne Key
# würde jeder Chat/jede Klassifizierung erst zur Laufzeit fehlschlagen.
if [ ! -f "$BACKEND_DIR/.env" ] || ! grep -q "^ANTHROPIC_API_KEY=" "$BACKEND_DIR/.env"; then
    echo "$(date): FEHLER — backend/.env fehlt oder hat keinen ANTHROPIC_API_KEY! Brain startet nicht." >> /tmp/brain_start.log
    exit 1
fi

# Backend nur starten wenn nicht schon läuft
pgrep -f "uvicorn app.main:app" > /dev/null || "$BACKEND_DIR/.venv/bin/uvicorn" app.main:app --port 8000 >> /tmp/brain_server.log 2>&1 &

# ngrok nur starten wenn nicht schon läuft
pgrep -f ngrok > /dev/null || /Users/sesp01-user/bin/ngrok start brain >> /tmp/ngrok.log 2>&1 &
