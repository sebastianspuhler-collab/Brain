#!/bin/bash
# Warte kurz bis Desktop geladen
sleep 5
cd /Users/sesp01-user/Documents/Prozessia-Brain

# API Key laden: .env → ~/.zprofile → ~/.zshrc (in dieser Priorität)
VAULT_DIR="$(dirname "$0")/.."
if [ -f "$VAULT_DIR/.env" ]; then
    source "$VAULT_DIR/.env" 2>/dev/null
fi
# Fallback: Shell-Profil laden falls Key noch nicht gesetzt
if [ -z "$ANTHROPIC_API_KEY" ]; then
    source ~/.zprofile 2>/dev/null || source ~/.zshrc 2>/dev/null || true
fi
# Letzter Fallback: macOS Keychain
if [ -z "$ANTHROPIC_API_KEY" ]; then
    ANTHROPIC_API_KEY=$(security find-generic-password -s ANTHROPIC_API_KEY -w 2>/dev/null) || true
fi

# Prüfen ob Key vorhanden
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "$(date): FEHLER — ANTHROPIC_API_KEY nicht gefunden! Brain startet nicht." >> /tmp/brain_start.log
    exit 1
fi

# Brain nur starten wenn nicht schon läuft
pgrep -f brain_server.py > /dev/null || /usr/bin/python3 _agent/brain_server.py &
# ngrok nur starten wenn nicht schon läuft
pgrep -f ngrok > /dev/null || /Users/sesp01-user/bin/ngrok start brain >> /tmp/ngrok.log 2>&1 &
