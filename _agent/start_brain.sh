#!/bin/bash
# Warte kurz bis Desktop geladen
sleep 5
cd /Users/sesp01-user/Documents/Prozessia-Brain
# API Key aus .env laden (nie den Key direkt hier eintragen)
source "$(dirname "$0")/../.env" 2>/dev/null || true
# Brain nur starten wenn nicht schon läuft
pgrep -f brain_server.py > /dev/null || /usr/bin/python3 _agent/brain_server.py &
# ngrok nur starten wenn nicht schon läuft  
pgrep -f ngrok > /dev/null || /Users/sesp01-user/bin/ngrok start brain >> /tmp/ngrok.log 2>&1 &
