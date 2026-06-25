#!/bin/bash
PID_FILE=~/Documents/Prozessia-Brain/_agent/watcher.pid
if [ -f "$PID_FILE" ]; then
    kill $(cat "$PID_FILE") 2>/dev/null
    rm "$PID_FILE"
    echo "Watcher gestoppt"
else
    echo "Kein laufender Watcher"
fi
