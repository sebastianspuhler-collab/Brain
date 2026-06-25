#!/bin/bash
cd ~/Documents/Prozessia-Brain
python3 _agent/watcher.py > _agent/logs/watcher.log 2>&1 &
echo $! > _agent/watcher.pid
echo "Watcher gestartet (PID: $(cat _agent/watcher.pid))"
