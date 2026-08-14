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
import re
import subprocess
import time

from app.config import get_settings
from app.services import calendar_lead_service, classify, email_indexer, gmail_client, memory, rag

logger = logging.getLogger("brain.background")

INBOX_POLL_SECONDS = 30
EMAIL_POLL_SECONDS = 300
GIT_SYNC_SECONDS   = 600  # alle 10 Minuten git pull
CALENDAR_LEAD_POLL_SECONDS = 1800  # alle 30 Minuten - Kalender ändert sich seltener als Mails
ATTACHMENT_POLL_SECONDS = 900  # alle 15 Minuten - Anhänge sind seltener als neue Mails
REORGANIZE_POLL_SECONDS = 1800  # alle 30 Minuten - reines Aufräumen, nicht zeitkritisch
_SKIP_EXT = {".js", ".ts", ".map", ".css", ".lock", ".yml", ".yaml"}
_SKIP_NAMES = {".DS_Store", "Thumbs.db"}
# Word/Excel legen beim Öffnen einer Datei eine Sperrdatei "~$name.docx" daneben.
# Die enthält keinen Dokumentinhalt, scheiterte deshalb zwangsläufig an der
# Klassifizierung und landete in _inbox/_fehler/ (dort lagen 2 davon, 2026-08-11).
_SKIP_PREFIXES = ("~$",)

# Gemeinsamer Gmail-Rate-Limit-Cooldown (2026-07-25): email_indexer_loop UND
# attachment_backfill_loop rufen unabhängig voneinander Gmail auf. Ohne diesen
# gemeinsamen Cooldown liefen beide bei einem 429 ("User-rate limit exceeded")
# einfach nach ihrem eigenen festen Intervall wieder los, was das Rate-Limit-
# Fenster live beobachtet immer weiter nach hinten verschoben hat, statt es
# abklingen zu lassen.
_gmail_cooldown_until = 0.0
_GMAIL_COOLDOWN_SECONDS = 20 * 60


def _gmail_in_cooldown() -> bool:
    return time.monotonic() < _gmail_cooldown_until


def _note_gmail_error(exc: Exception) -> None:
    global _gmail_cooldown_until
    if "rateLimitExceeded" in str(exc) or " 429 " in str(exc):
        _gmail_cooldown_until = time.monotonic() + _GMAIL_COOLDOWN_SECONDS
        logger.warning("Gmail Rate-Limit erkannt - Cooldown fuer %ds gesetzt", _GMAIL_COOLDOWN_SECONDS)


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
        # https://[alte-credentials@]github.com/... → https://PAT@github.com/...
        # Erst eventuell schon eingebettete Zugangsdaten aus einem vorherigen
        # Aufruf entfernen (Bug 2026-08-14): diese Funktion wird bei JEDEM
        # Sync-Zyklus (git_pull_vault UND git_push_vault, alle 10 Min) erneut
        # auf der zuletzt gesetzten Remote-URL aufgerufen - ohne das Entfernen
        # haengte jeder weitere Aufruf ein zusaetzliches "PAT@" vor die schon
        # vorhandenen Zugangsdaten ("https://PAT@PAT@github.com/..."), git/curl
        # lehnten das dann mit "URL rejected: Bad hostname" ab. Muss idempotent
        # sein, egal wie oft sie auf derselben URL laeuft.
        url_ohne_credentials = re.sub(r"://[^/@]+@", "://", url, count=1)
        return url_ohne_credentials.replace("https://", f"https://{pat}@", 1)
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


_GIT_SYNC_WARNING = "- [ ] ⚠️ Git-Sync hängt seit mehreren Zyklen (siehe Backend-Log `git pull/push Fehler`) - manuell prüfen @Sebastian"
_pull_fail_count = 0
_pull_warned = False


def _set_git_sync_warning(active: bool) -> None:
    """Schreibt/entfernt eine Zeile in Offene Aufgaben von context.md, wenn der
    Git-Sync mehrfach hintereinander fehlschlägt - sonst blieb ein hängender
    Sync (wie am 12.08.2026, tagelang unbemerkt, weil pull/push-Fehler nur ins
    Backend-Log gingen, das niemand routinemäßig ansieht) komplett unsichtbar."""
    global _pull_warned
    settings = get_settings()
    path = settings.vault_path / "_agent" / "context.md"
    if not path.exists():
        return
    try:
        content = path.read_text(encoding="utf-8")
        has_warning = _GIT_SYNC_WARNING in content
        if active and not has_warning:
            marker = "## Offene Aufgaben\n"
            if marker in content:
                content = content.replace(marker, f"{marker}{_GIT_SYNC_WARNING}\n", 1)
                path.write_text(content, encoding="utf-8")
            _pull_warned = True
        elif not active and has_warning:
            content = content.replace(f"{_GIT_SYNC_WARNING}\n", "", 1)
            path.write_text(content, encoding="utf-8")
            _pull_warned = False
    except Exception:
        logger.exception("Git-Sync-Warnung in context.md konnte nicht aktualisiert werden")


def git_pull_vault() -> bool:
    """Führt git pull im Vault aus. Gibt True zurück wenn erfolgreich."""
    global _pull_fail_count
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
            _pull_fail_count = 0
            if _pull_warned:
                _set_git_sync_warning(False)
            return True
        logger.warning("git pull Fehler: %s", result.stderr.strip()[:200])
        # Bei einem Konflikt (z.B. Mac/VPS-Divergenz bei generierten Dateien,
        # siehe .gitattributes) sofort aufräumen statt bis zum nächsten
        # Zyklus (GIT_SYNC_SECONDS) hängen zu lassen - sonst liegen bis zu
        # 10 Minuten lang Dateien mit Konflikt-Markern im Arbeitsverzeichnis,
        # die z.B. der Inbox-Watcher zwischenzeitlich einliest.
        _abort_stuck_rebase(vault, env)
        _pull_fail_count += 1
        if _pull_fail_count >= 3 and not _pull_warned:
            _set_git_sync_warning(True)
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
    """Alle 10 Min: zuerst eigene lokale Änderungen committen+pushen, DANN
    pullen, dann nochmal pushen (falls der Pull neue lokale Commits durch
    den Rebase erzeugt hat).

    Reihenfolge ist hier der Kern: wenn zuerst gepullt würde, während z.B.
    der Reorganize-Job (siehe vault_reorganize_loop) Dateien bereits umbenannt/
    verschoben, aber noch nicht committet hat, kollidiert `git pull --rebase`
    mit diesen UNTRACKED Dateien ("would be overwritten by checkout") und
    bricht komplett ab - der anschließende Push scheitert dann ebenfalls
    (non-fast-forward), beides bisher lautlos. Genau das hat den VPS-Sync
    vom 04.08. bis 12.08.2026 lahmgelegt (82 lokale Commits nie gepusht).
    Indem zuerst committet wird, ist beim Pull nichts mehr untracked - ein echter
    Konflikt wird dann von git selbst (ggf. per .gitattributes merge=ours/
    merge=union) sauber aufgelöst statt den ganzen Zyklus zu blockieren."""
    await asyncio.sleep(30)  # Warten bis der Rest gestartet ist
    while True:
        try:
            await asyncio.to_thread(git_push_vault)
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
            # Der Cache muss hier mitgeprüft werden, nicht erst in run_inbox()
            # (Sebastian, 2026-07-27): sonst gilt eine bereits verarbeitete, aber
            # noch in _inbox/ liegende Datei alle 30 Sekunden erneut als "neu",
            # run_inbox() läuft an, findet nichts zu tun und meldet "Inbox leer" -
            # dauerhaft, im Log ununterscheidbar von echter Arbeit. Genau das lief
            # hier seit dem 24.07. mit 112 Karteileichen im Ordner.
            bereits_verarbeitet = classify._load_cache()
            neue = [
                f for f in inbox.rglob("*")
                if f.is_file()
                and f.suffix.lower() not in _SKIP_EXT
                and f.name not in _SKIP_NAMES
                and not f.name.startswith(".")
                and not f.name.startswith(_SKIP_PREFIXES)
                and "_fehler" not in str(f)
                and "node_modules" not in str(f)
                and "Branding" not in str(f)
                and str(f) not in bereits_verarbeitet
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
        if _gmail_in_cooldown():
            await asyncio.sleep(EMAIL_POLL_SECONDS)
            continue
        try:
            await asyncio.to_thread(email_indexer.index_new_emails, False)
        except Exception as exc:
            logger.exception("Email-Indexer Fehler")
            _note_gmail_error(exc)
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
        if _gmail_in_cooldown():
            await asyncio.sleep(ATTACHMENT_POLL_SECONDS)
            continue
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
                    for i, att in enumerate(attachments):
                        # WICHTIG (2026-07-25, live verifiziert): Gmails
                        # attachmentId ist NICHT stabil - ändert sich bei jedem
                        # get_attachments()-Aufruf für denselben Anhang. Als
                        # Dedup-Key komplett nutzlos, das ließ hier JEDEN
                        # Anhang bei jedem 15-Minuten-Zyklus für immer als
                        # "neu" gelten -> endloser Redownload, Inbox-Backlog
                        # wuchs unbegrenzt. Index+Dateiname (stabil pro Mail,
                        # solange get_attachments() dieselbe Reihenfolge
                        # liefert) statt attachmentId als Schlüssel.
                        key = f"{message_id}:{i}:{att['filename']}"
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
        except Exception as exc:
            logger.exception("Attachment-Backfill Fehler")
            _note_gmail_error(exc)
        await asyncio.sleep(ATTACHMENT_POLL_SECONDS)


async def vault_reorganize_loop() -> None:
    """Räumt den Vault laufend automatisch auf (Sebastian, 2026-08-11:
    Kunden/Schaufler/Dokumente/ war auf ~110 lose Dateien angewachsen und
    dadurch faktisch unbrowsbar - "das System muss das automatisch neu
    sortieren"; erweitert 2026-08-14 um MD/Original-Trennung und
    Kategorie-Unterordner ab einer Schwelle, siehe classify.reorganize_vault()
    Docstring für die drei Teilschritte). process_file() legt die
    Zielstruktur seit 2026-08-14 für NEUE Dateien direkt an; dieser Loop holt
    bestehende, schon vollgelaufene oder noch nicht migrierte Ordner nach und
    hält künftig neu wachsende Ordner laufend aufgeräumt, ohne dass Sebastian
    das manuell anstoßen muss. classify.reorganize_vault() ist idempotent -
    ein Durchlauf ohne etwas zu tun ist die Regel, nicht die Ausnahme, sobald
    einmal aufgeräumt."""
    await asyncio.sleep(120)  # nach RAG-Laden und den anderen Loops starten
    while True:
        try:
            ergebnisse = await asyncio.to_thread(classify.reorganize_vault)
            if ergebnisse:
                gesamt = sum(e.get("verschoben", e.get("aufgeloest", 0)) for e in ergebnisse)
                logger.info(
                    "Vault-Aufräumen: %d Datei(en) in %d Ordner(n) neu einsortiert",
                    gesamt, len(ergebnisse),
                )
        except Exception:
            logger.exception("Vault-Reorganize Fehler")
        await asyncio.sleep(REORGANIZE_POLL_SECONDS)
