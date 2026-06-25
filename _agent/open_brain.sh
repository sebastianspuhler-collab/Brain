#!/bin/bash
cd ~/Documents/Prozessia-Brain

# Server starten falls nicht läuft
if ! lsof -ti:3001 > /dev/null 2>&1; then
  python3 _agent/brain_server.py > /tmp/brain_server.log 2>&1 &
  sleep 2
fi

open prozessia_brain_ui.html
