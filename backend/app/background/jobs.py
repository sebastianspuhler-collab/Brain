"""Konsolidierte Hintergrundjobs.

Im Original gab es ZWEI unabhängige Inbox-Watcher (_agent/watcher.py mit watchdog
für systemd/Cron, UND einen 30s-Polling-Thread direkt in brain_server.py) - beide
lösten dieselbe Verarbeitung aus. Hier: nur noch der Polling-Ansatz, weil er ohne
zusätzliche Prozesse/Dienste auskommt und in Docker unkomplizierter ist.
"""
import asyncio
import logging

from app.config import get_settings
from app.services import classify, email_indexer, memory, rag

logger = logging.getLogger("brain.background")

INBOX_POLL_SECONDS = 30
EMAIL_POLL_SECONDS = 300
_SKIP_EXT = {".js", ".ts", ".map", ".css", ".lock", ".yml", ".yaml"}
_SKIP_NAMES = {".DS_Store", "Thumbs.db"}


def load_rag_blocking() -> None:
    rag.load()


async def inbox_watcher_loop() -> None:
    """Ersetzt _agent/watcher.py (watchdog) UND den alten Inline-Poller - nur noch einer."""
    settings = get_settings()
    while True:
        await asyncio.sleep(INBOX_POLL_SECONDS)
        try:
            inbox = settings.inbox_dir
            if not inbox.exists():
                continue
            neue = [
                f for f in inbox.rglob("*")
                if f.is_file()
                and f.suffix.lower() not in _SKIP_EXT
                and f.name not in _SKIP_NAMES
                and not f.name.startswith(".")
                and "_fehler" not in str(f)
                and "node_modules" not in str(f)
                and "Branding" not in str(f)
            ]
            if neue:
                logger.info("Inbox-Watcher: %d neue Datei(en) -> verarbeite...", len(neue))
                await asyncio.to_thread(classify.run_inbox)
                new_files = await asyncio.to_thread(rag.reindex_new_files)
                for rel, content in new_files:
                    await asyncio.to_thread(memory.learn_from_file, rel, content)
        except Exception:
            logger.exception("Inbox-Watcher Fehler")


async def email_indexer_loop() -> None:
    """Einmaliger Deep-Scan (500 Mails) beim ersten Start, danach alle 5 Minuten 50 neue."""
    await asyncio.sleep(15)  # RAG + Clients Zeit zum Laden geben
    if not email_indexer.deep_scan_done_path().exists():
        logger.info("Email Deep-Scan: lese 500 Mails ein (einmalig)...")
        try:
            await asyncio.to_thread(email_indexer.index_new_emails, True)
            email_indexer.deep_scan_done_path().parent.mkdir(parents=True, exist_ok=True)
            email_indexer.deep_scan_done_path().write_text("done")
        except Exception:
            logger.exception("Email Deep-Scan Fehler")
    while True:
        try:
            await asyncio.to_thread(email_indexer.index_new_emails, False)
        except Exception:
            logger.exception("Email-Indexer Fehler")
        await asyncio.sleep(EMAIL_POLL_SECONDS)
