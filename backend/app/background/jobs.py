"""Konsolidierte Hintergrundjobs.

Im Original gab es ZWEI unabhängige Inbox-Watcher (_agent/watcher.py mit watchdog
für systemd/Cron, UND einen 30s-Polling-Thread direkt in brain_server.py) - beide
lösten dieselbe Verarbeitung aus. Hier: nur noch der Polling-Ansatz, weil er ohne
zusätzliche Prozesse/Dienste auskommt und in Docker unkomplizierter ist.
"""
import asyncio
import logging
import os
import subprocess

from app.config import get_settings
from app.services import calendar_lead_service, classify, email_indexer, memory, rag

logger = logging.getLogger("brain.background")

INBOX_POLL_SECONDS = 30
EMAIL_POLL_SECONDS = 300
GIT_SYNC_SECONDS   = 600  # alle 10 Minuten git pull
CALENDAR_LEAD_POLL_SECONDS = 1800  # alle 30 Minuten - Kalender ändert sich seltener als Mails
_SKIP_EXT = {".js", ".ts", ".map", ".css", ".lock", ".yml", ".yaml"}
_SKIP_NAMES = {".DS_Store", "Thumbs.db"}


def load_rag_blocking() -> None:
    rag.load()


def _git_remote_with_pat(vault_path, pat: str) -> str | None:
    """Gibt die Remote-URL mit eingebettetem PAT zurück, oder None wenn kein Remote."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=vault_path, capture_output=True, text=True, timeout=10,
        )
        url = result.stdout.strip()
        if not url or "github.com" not in url:
            return None
        # https://github.com/... → https://PAT@github.com/...
        return url.replace("https://", f"https://{pat}@")
    except Exception:
        return None


def git_pull_vault() -> bool:
    """Führt git pull im Vault aus. Gibt True zurück wenn erfolgreich."""
    settings = get_settings()
    vault = settings.vault_path
    pat = settings.git_pat
    if not vault.exists():
        return False
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        cmd = ["git", "pull", "--rebase", "--autostash"]
        if pat:
            remote_url = _git_remote_with_pat(vault, pat)
            if remote_url:
                subprocess.run(
                    ["git", "remote", "set-url", "origin", remote_url],
                    cwd=vault, capture_output=True, timeout=10, env=env,
                )
        result = subprocess.run(cmd, cwd=vault, capture_output=True, text=True, timeout=60, env=env)
        if result.returncode == 0:
            logger.info("git pull: %s", result.stdout.strip() or "up to date")
            return True
        logger.warning("git pull Fehler: %s", result.stderr.strip()[:200])
        return False
    except Exception as exc:
        logger.warning("git pull Exception: %s", exc)
        return False


def git_push_vault(message: str = "brain: auto-sync") -> bool:
    """Committed und pushed lokale Änderungen (memory.md, context.md, etc.)."""
    settings = get_settings()
    vault = settings.vault_path
    pat = settings.git_pat
    if not vault.exists() or not pat:
        return False
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_AUTHOR_NAME"] = "Prozessia Brain"
    env["GIT_AUTHOR_EMAIL"] = "brain@prozessia.de"
    env["GIT_COMMITTER_NAME"] = "Prozessia Brain"
    env["GIT_COMMITTER_EMAIL"] = "brain@prozessia.de"
    try:
        # Nur _agent/*.md committen (memory, context, logs) - keine Binärdateien
        subprocess.run(
            ["git", "add", "_agent/memory.md", "_agent/context.md",
             "_agent/prozessia.md", "_agent/logs/inbox_log.md"],
            cwd=vault, capture_output=True, timeout=10, env=env,
        )
        status = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=vault, timeout=10, env=env,
        )
        if status.returncode == 0:
            return True  # nichts staged, kein Push nötig

        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=vault, capture_output=True, timeout=15, env=env,
        )
        remote_url = _git_remote_with_pat(vault, pat)
        if remote_url:
            subprocess.run(
                ["git", "remote", "set-url", "origin", remote_url],
                cwd=vault, capture_output=True, timeout=10, env=env,
            )
        result = subprocess.run(
            ["git", "push", "origin", "HEAD"],
            cwd=vault, capture_output=True, text=True, timeout=60, env=env,
        )
        if result.returncode == 0:
            logger.info("git push: OK")
            return True
        logger.warning("git push Fehler: %s", result.stderr.strip()[:200])
        return False
    except Exception as exc:
        logger.warning("git push Exception: %s", exc)
        return False


async def git_sync_loop() -> None:
    """Zieht alle 10 Min den neuesten Stand vom Remote-Repo (Mac → VPS-Sync)."""
    await asyncio.sleep(30)  # Warten bis der Rest gestartet ist
    while True:
        try:
            await asyncio.to_thread(git_pull_vault)
        except Exception:
            logger.exception("Git-Sync Fehler")
        await asyncio.sleep(GIT_SYNC_SECONDS)


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


async def calendar_lead_loop() -> None:
    """Prüft periodisch den Kalender auf Erstgespräche mit neuen potenziellen
    Kunden (Sebastian: "man sollte allgemein erkennen, wann ein Erstgespräch
    per Teams stattfindet") und legt dafür automatisch Lead-Notizen in Leads/
    an, statt nur auf feste Namensmuster zu warten."""
    await asyncio.sleep(45)
    while True:
        try:
            found = await asyncio.to_thread(calendar_lead_service.scan_for_new_leads)
            if found:
                logger.info("Kalender-Lead-Scan: neue Erstgespräche erkannt: %s", ", ".join(found))
                new_files = await asyncio.to_thread(rag.reindex_new_files)
                for rel, content in new_files:
                    await asyncio.to_thread(memory.learn_from_file, rel, content)
        except Exception:
            logger.exception("Kalender-Lead-Scan Fehler")
        await asyncio.sleep(CALENDAR_LEAD_POLL_SECONDS)
