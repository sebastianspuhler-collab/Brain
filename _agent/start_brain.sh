#!/bin/bash
# Startet das aktuelle FastAPI-Backend (backend/app/main.py) als Vordergrund-
# prozess, den launchd direkt verfolgt (siehe "exec" unten).
#
# Aktualisiert 2026-07-17: das alte Skript startete noch _agent/brain_server.py
# (die Pre-FastAPI-Architektur von vor der Backend-Migration). Zusätzlich lief
# der Server bisher im Hintergrund (per "&") - dadurch endete der von launchd
# direkt verfolgte Wrapper-Prozess sofort, launchd stufte den Job als beendet
# ein und killte die ganze Prozessgruppe inklusive des gerade erst gestarteten
# uvicorn-Prozesses, bevor der überhaupt fertig hochfahren konnte (endlose
# Neustart-Schleife des Wrappers, nie ein stabil laufender Server). Jetzt läuft
# uvicorn per "exec" als der Prozess, den launchd tatsächlich überwacht.

sleep 5

VAULT_DIR="/Users/sesp01-user/vault/Prozessia-Brain"
BACKEND_DIR="$VAULT_DIR/backend"
cd "$BACKEND_DIR" || exit 1

if [ ! -f "$BACKEND_DIR/.env" ] || ! grep -q "^ANTHROPIC_API_KEY=" "$BACKEND_DIR/.env"; then
    echo "$(date): FEHLER — backend/.env fehlt oder hat keinen ANTHROPIC_API_KEY! Brain startet nicht." >> /tmp/brain_start.log
    exit 1
fi

# ngrok hat seinen eigenen Lebenszyklus, läuft weiterhin im Hintergrund
pgrep -f ngrok > /dev/null || nohup /Users/sesp01-user/bin/ngrok start brain >> /tmp/ngrok.log 2>&1 &

# uvicorn als Vordergrundprozess starten (exec ersetzt den bash-Prozess direkt,
# statt ein Kind zu erzeugen - launchds KeepAlive überwacht dadurch uvicorn
# selbst, nicht nur den Wrapper)
exec "$BACKEND_DIR/.venv/bin/uvicorn" app.main:app --port 8000
