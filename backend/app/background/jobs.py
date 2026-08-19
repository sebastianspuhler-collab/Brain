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
import time

from app.config import get_settings
from app.services import calendar_lead_service, classify, email_indexer, gmail_client, meeting_reminder_service, memory, rag

logger = logging.getLogger("brain.background")

INBOX_POLL_SECONDS = 30
EMAIL_POLL_SECONDS = 300
CALENDAR_LEAD_POLL_SECONDS = 1800  # alle 30 Minuten - Kalender ändert sich seltener als Mails
ATTACHMENT_POLL_SECONDS = 900  # alle 15 Minuten - Anhänge sind seltener als neue Mails
REMINDER_POLL_SECONDS = 300  # alle 5 Minuten - Lead-Zeit ist nur 60 Minuten, muss engmaschiger prüfen
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


async def meeting_reminder_loop() -> None:
    """Legt automatisch einen Gmail-Entwurf an, wenn ein Kalendertermin mit
    externen Teilnehmern kurz bevorsteht (Sebastian, 2026-08-16) - bewusst nur
    ein Entwurf, kein Auto-Versand, siehe meeting_reminder_service.py."""
    await asyncio.sleep(90)
    while True:
        try:
            created = await asyncio.to_thread(meeting_reminder_service.scan_and_draft_reminders)
            if created:
                logger.info("Termin-Erinnerung(en) als Entwurf angelegt: %s", ", ".join(created))
        except Exception:
            logger.exception("Termin-Erinnerung-Scan Fehler")
        await asyncio.sleep(REMINDER_POLL_SECONDS)


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
