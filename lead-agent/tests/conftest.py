import sys
from pathlib import Path

# lead-agent/ ist ein flaches Modul-Verzeichnis (kein app.*-Package wie
# backend/) - hier explizit auf sys.path setzen, damit `import close_client`
# etc. unabhängig davon funktioniert, von wo aus pytest gestartet wird.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
