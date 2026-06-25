import time
import subprocess
import sys
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

VAULT_PATH = Path.home() / "Documents" / "Prozessia-Brain"
HEARTBEAT = str(VAULT_PATH / "_agent" / "heartbeat.py")

class InboxHandler(FileSystemEventHandler):
    def __init__(self):
        self.last_run = 0

    def on_created(self, event):
        now = time.time()
        if now - self.last_run < 3:
            return
        if event.src_path.endswith(".DS_Store"):
            return
        print(f"Neue Datei erkannt: {event.src_path}")
        time.sleep(2)
        self.last_run = time.time()
        subprocess.run([sys.executable, HEARTBEAT])

if __name__ == "__main__":
    inbox = str(VAULT_PATH / "_inbox")
    print(f"Watcher aktiv: {inbox}")
    observer = Observer()
    observer.schedule(InboxHandler(), inbox, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
