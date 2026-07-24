"""Konsolidierte Hintergrundjobs.

Im Original gab es ZWEI unabhängige Inbox-Watcher (_agent/watcher.py mit watchdog
für systemd/Cron, UND einen 30s-Polling-Thread direkt in brain_server.py) - beide
lösten dieselbe Verarbeitung aus. Hier: nur noch der Polling-Ansatz, weil er ohne
zusätzliche Prozesse/Dienste auskommt und in Docker unkomplizierter ist.
"""
import asyncio
import json
import logging
import os
import subprocess

from app.config import get_settings
from app.services import calendar_lead_service, classify, email_indexer, gmail_client, memory, rag

logger = logging.getLogger("brain.background")

INBOX_POLL_SECONDS = 30
EMAIL_POLL_SECONDS = 300
GIT_SYNC_SECONDS   = 600  # alle 10 Minuten git pull
CALENDAR_LEAD_POLL_SECONDS = 1800  # alle 30 Minuten - Kalender ändert sich seltener als Mails
ATTACHMENT_POLL_SECONDS = 900  # alle 15 Minuten - Anhänge sind seltener als neue Mails
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


def _abort_stuck_rebase(vault, env) -> None:
    """Bricht einen hängengebliebenen Rebase ab, bevor ein neuer git pull
    versucht wird - ohne das würde ein einmal fehlgeschlagener Rebase (z.B.
    durch einen Binärdatei-Konflikt bei _agent/vault.index, siehe
    .gitattributes) den Sync dauerhaft blockieren: jeder weitere Aufruf
    dieser Funktion würde denselben Rebase-in-Progress-Fehler wiederholen,
    statt es erneut zu versuchen. git rebase --abort ist ein No-Op (Fehler
    wird ignoriert), wenn gerade kein Rebase läuft."""
    if (vault / ".git" / "rebase-merge").exists() or (vault / ".git" / "rebase-apply").exists():
        subprocess.run(["git", "rebase", "--abort"], cwd=vault, capture_output=True, timeout=30, env=env)
        logger.warning("git pull: hängenden Rebase vor neuem Versuch abgebrochen")


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
        _abort_stuck_rebase(vault, env)
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
        # Bei einem Konflikt (z.B. Mac/VPS-Divergenz bei generierten Dateien,
        # siehe .gitattributes) sofort aufräumen statt bis zum nächsten
        # Zyklus (GIT_SYNC_SECONDS) hängen zu lassen - sonst liegen bis zu
        # 10 Minuten lang Dateien mit Konflikt-Markern im Arbeitsverzeichnis,
        # die z.B. der Inbox-Watcher zwischenzeitlich einliest.
        _abort_stuck_rebase(vault, env)
        return False
    except Exception as exc:
        logger.warning("git pull Exception: %s", exc)
        return False


def git_push_vault(message: str = "brain: auto-sync") -> bool:
    """Committed und pushed ALLE lokalen Änderungen - nicht mehr nur die vier
    _agent/*.md-Dateien (Sebastian, 2026-07-20: nur noch der VPS führt das
    Backend aus, das Laptop-Dateisystem muss dafür aber vollständig synchron
    bleiben, sonst fehlen dort neu einsortierte Kundendokumente/Anhänge -
    diese Funktion wurde bis dahin nirgends aufgerufen, der VPS hat seine
    eigenen classify()-Ablagen nie automatisch gepusht)."""
    settings = get_settings()
    vault = settings.vault_path
    pat = settings.git_pat
    if not vault.exists():
        return False
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_AUTHOR_NAME"] = "Prozessia Brain"
    env["GIT_AUTHOR_EMAIL"] = "brain@prozessia.de"
    env["GIT_COMMITTER_NAME"] = "Prozessia Brain"
    env["GIT_COMMITTER_EMAIL"] = "brain@prozessia.de"
    try:
        subprocess.run(
            ["git", "add", "-A"],
            cwd=vault, capture_output=True, timeout=30, env=env,
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
        if pat:
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
    """Alle 10 Min: zuerst pullen (Mac → VPS), danach eigene Änderungen pushen
    (VPS → Mac) - bidirektional, damit das Laptop-Dateisystem sieht, was der
    VPS selbst einsortiert hat (siehe git_push_vault())."""
    await asyncio.sleep(30)  # Warten bis der Rest gestartet ist
    while True:
        try:
            await asyncio.to_thread(git_pull_vault)
            await asyncio.to_thread(git_push_vault)
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


def _downloaded_attachments_path():
    return get_settings().agent_dir / "downloaded_attachments.json"


def _load_downloaded_attachments() -> set[str]:
    path = _downloaded_attachments_path()
    if not path.exists():
        return set()
    try:
        return set(json.loads(path.read_text(encoding="utf-8")))
    except Exception:
        return set()


def _save_downloaded_attachments(ids: set[str]) -> None:
    path = _downloaded_attachments_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(ids), ensure_ascii=False, indent=2), encoding="utf-8")


async def attachment_backfill_loop() -> None:
    """Schließt eine echte Lücke (Sebastian, 2026-07-19): E-Mail-Text wird
    automatisch indexiert (email_indexer_loop), aber Anhänge landeten bisher
    NUR im Vault, wenn im Chat explizit das download_attachment-Tool
    aufgerufen wurde (tools.py:_download_attachment) - nie automatisch. Eine
    konkrete Bestellung war deshalb im Vault nicht auffindbar, obwohl sie
    vermutlich nur als Mail-Anhang existierte. Speichert neue Anhänge nur nach
    _inbox/ - die bereits laufende inbox_watcher_loop() übernimmt Klassifizierung,
    Datums-Erkennung und Ablage, keine doppelte Verarbeitungslogik hier."""
    settings = get_settings()
    await asyncio.sleep(60)
    while True:
        try:
            if gmail_client.is_authenticated():
                bekannt = await asyncio.to_thread(_load_downloaded_attachments)
                raw_mails = await asyncio.to_thread(gmail_client.get_emails, top=500)
                neu = 0
                for mail in raw_mails:
                    message_id = mail.get("id", "")
                    if not message_id:
                        continue
                    attachments = await asyncio.to_thread(gmail_client.get_attachments, message_id)
                    for att in attachments:
                        key = f"{message_id}:{att['attachmentId']}"
                        if key in bekannt:
                            continue
                        # .ics: reine Kalender-Termindaten, kein Dokument mit
                        # eigenem Inhalt (Termine laufen schon über calendar_
                        # lead_service) - würde nur Kunden-Ordner mit Leernotizen
                        # zumüllen, ohne jemals gesucht/gefunden zu werden.
                        if att["filename"].lower().endswith(".ics"):
                            bekannt.add(key)
                            continue
                        data = await asyncio.to_thread(
                            gmail_client.download_attachment, message_id, att["attachmentId"]
                        )
                        bekannt.add(key)  # auch bei leerem Ergebnis merken - kein Endlos-Retry
                        if not data:
                            continue
                        settings.inbox_dir.mkdir(parents=True, exist_ok=True)
                        # Präfix mit Kurz-Message-ID: viele Anhänge heißen
                        # generisch identisch (z.B. "image001.png", mehrfach in
                        # verschiedenen Mails) - ohne das würden spätere
                        # Downloads frühere in _inbox/ überschreiben, BEVOR
                        # classify() sie verarbeitet hat (live beobachtet:
                        # 135 heruntergeladene Anhänge wurden so auf 53 Dateien
                        # reduziert, stiller Datenverlust).
                        dest_name = f"{message_id[:10]}-{att['filename']}"
                        (settings.inbox_dir / dest_name).write_bytes(data)
                        neu += 1
                await asyncio.to_thread(_save_downloaded_attachments, bekannt)
                if neu:
                    logger.info("Attachment-Backfill: %d neue Anhang/Anhänge nach _inbox/ gespeichert", neu)
        except Exception:
            logger.exception("Attachment-Backfill Fehler")
        await asyncio.sleep(ATTACHMENT_POLL_SECONDS)
