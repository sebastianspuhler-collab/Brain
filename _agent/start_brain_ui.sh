#!/bin/bash
source ~/.zshrc
cd ~/Documents/Prozessia-Brain
echo "🧠 Prozessia Brain startet..."
python3 -m streamlit run _agent/brain_ui.py --server.port 8501 --server.headless false
