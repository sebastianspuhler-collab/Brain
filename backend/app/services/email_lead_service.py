"""Erkennt aus eingehenden E-Mails automatisch neue potenzielle Kunden - das
E-Mail-Gegenstück zu calendar_lead_service.py (dort für Kalendertermine).

Lücke bisher: email_indexer._match_customer()/_match_lead() ordnen eine Mail
nur EXISTIERENDEN Kunden/Leads zu (Namensabgleich gegen bereits vorhandene
Kunden-Ordner/Lead-Dateien). Eine Erstanfrage eines komplett neuen, noch
unbekannten Absenders landete deshalb nur im generischen _agent/email_cache/
und tauchte nirgends im Dashboard auf - Sebastian, 2026-08-06: "kein
vergessener Interessent", bisher nur für Kalendertermine abgedeckt.

Dieselbe Bauweise wie calendar_lead_service.py bewusst wiederverwendet:
Haiku entscheidet pro Mail dynamisch statt fester Namensmuster, und dieselbe
retry-sichere Cache-Disziplin (nur ein definitives Klassifizierungs-Ergebnis
markiert eine Mail dauerhaft als "geprüft" - ein gescheiterter LLM-Call wird
beim nächsten Indexer-Lauf erneut versucht, siehe dortiger Kommentar zum
TopDown-Bug)."""
import json
import re
from datetime import datetime

from app.config import get_settings
from app.constants import Models
from app.services import classify, memory
from app.services.anthropic_client import complete_json

# email_indexer importiert seinerseits dieses Modul (ruft consider_new_lead()
# auf) - ein Top-Level-Import hier würde einen Zirkelbezug erzeugen, daher
# lazy innerhalb der Funktionen, die _date_iso()/_write_lead_correspondence()
# tatsächlich brauchen.

# Günstiger Vorfilter vor jedem LLM-Call: offensichtliche System-/Massenmail-
# Absender kosten keine Klassifizierung und erzeugen nie einen Lead.
_AUTOMATED_MARKERS = ("noreply", "no-reply", "no.reply", "newsletter", "mailer-daemon", "postmaster")


def _cache_path():
    return get_settings().agent_dir / "logs" / "email_lead_cache.json"


def _load_cache() -> set[str]:
    path = _cache_path()
    try:
        return set(json.loads(path.read_text(encoding="utf-8"))) if path.exists() else set()
    except Exception:
        return set()


def _save_cache(ids: set[str]) -> None:
    path = _cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(list(ids)), encoding="utf-8")


def _looks_automated(sender: str) -> bool:
    low = sender.lower()
    return any(marker in low for marker in _AUTOMATED_MARKERS)


def normalize_name(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _known_names() -> set[str]:
    """Bestehende Kunden UND Leads, normalisiert - wie
    calendar_lead_service._known_names(), damit ein Absender nicht doppelt als
    neuer Lead angelegt wird, obwohl schon ein Kunden-Ordner oder eine
    Lead-Datei existiert."""
    names = {normalize_name(n) for n in classify.list_customer_names()}
    names |= {normalize_name(n) for n in classify.list_lead_names()}
    return names


def _is_known(firma: str, known: set[str]) -> bool:
    """Substring-Abgleich wie calendar_lead_service._is_known() - dieselbe
    Begründung: Claude extrahiert oft den vollen Firmennamen, während der
    Ordner nur die Kurzform trägt."""
    needle = normalize_name(firma)
    if not needle:
        return False
    return any(k and (k in needle or needle in k) for k in known)


def _classify_email(sender: str, subject: str, body: str) -> dict | bool:
    """Wie calendar_lead_service._classify_event(): dict bei Erfolg (auch wenn
    keine Geschäftsanfrage), False NUR bei gescheitertem LLM-Call. Nutzt
    ausschließlich Absender/Betreff/Textauszug der tatsächlichen Mail als
    Kontext - es wird nichts ergänzt, was nicht wörtlich in der Mail steht."""
    prompt = f"""Du prüfst eine eingehende E-Mail an Sebastian Spuhler (Prozessia GbR,
KI-Agentur, Saarbrücken) auf eine ECHTE GESCHÄFTSANFRAGE eines neuen, noch
unbekannten potenziellen Kunden/Interessenten.

Von: {sender}
Betreff: {subject}
Textauszug: {body[:500]}

Ist das eine echte neue Geschäftsanfrage/ein Erstkontakt (kein Spam, keine
Newsletter-/Marketing-Mail, kein interner Vorgang, keine
Lieferanten-/Dienstleister-Rechnung, keine Bewerbung/Recruiting, keine
automatisierte Benachrichtigung)? Wenn ja, extrahiere die Firma (falls keine
erkennbar: den Namen der Person).

NUR JSON:
{{"ist_geschaeftsanfrage": true, "firma": "Firmenname oder Personenname"}}
Wenn nein oder unklar: {{"ist_geschaeftsanfrage": false}}"""
    try:
        text = complete_json(prompt, model=Models.HAIKU, max_tokens=200).strip()
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return False
        return json.loads(match.group())
    except Exception:
        return False


def _write_lead_stub(firma: str, sender: str, subject: str, date: str) -> str:
    """Schreibt die Lead-Notiz, analog zu
    calendar_lead_service._write_lead_stub(). Gibt den sanitierten Namen
    zurück (ohne Datumspräfix), damit consider_new_lead() denselben Namen für
    den Korrespondenz-Ordner verwendet wie hier im Dateinamen - EIN Ort für
    die Sanitierung statt zweier potenziell abweichender Kopien."""
    from app.services import email_indexer

    settings = get_settings()
    leads_dir = settings.vault_path / "Leads"
    leads_dir.mkdir(parents=True, exist_ok=True)
    datum = email_indexer._date_iso(date) or datetime.now().strftime("%Y-%m-%d")
    safe_name = re.sub(r"[^\w\s-]", "", firma)[:40].strip().replace(" ", "-")
    path = leads_dir / f"{datum}-{safe_name}.md"
    if not path.exists():
        path.write_text(
            f"""---
tags:
  - Lead
  - E-Mail-Erstkontakt
quelle: E-Mail
datum: {datum}
kategorie: Lead
---

# {firma}

## Zusammenfassung
Automatisch aus einer eingehenden E-Mail erkannter Erstkontakt mit einem
neuen potenziellen Kunden. Noch kein Gespräch/Dokument vorhanden - diese
Notiz ist der erste Anhaltspunkt, wird ergänzt sobald mehr Material eintrifft.

## Erste Nachricht
Von: {sender}
Betreff: {subject}
""",
            encoding="utf-8",
        )
    return safe_name


def consider_new_lead(eid: str, sender: str, subject: str, date: str, body: str) -> str | None:
    """Wird aus email_indexer.index_new_emails() für jede Mail aufgerufen, die
    weder zu einem bestehenden Kunden noch Lead passt (_match_customer()/
    _match_lead() beide None). Gibt den erkannten Firmennamen zurück (fürs
    Logging) oder None."""
    if not sender or not eid or _looks_automated(sender):
        return None

    cache = _load_cache()
    if eid in cache:
        return None

    result = _classify_email(sender, subject, body)
    if result is False:
        # Fehlgeschlagene Klassifizierung - NICHT cachen, der nächste
        # Indexer-Lauf (alle 5 Min., siehe jobs.py::email_indexer_loop)
        # versucht es erneut, statt die Mail für immer zu vergessen.
        return None

    cache.add(eid)
    _save_cache(cache)

    if not result.get("ist_geschaeftsanfrage"):
        return None
    firma = (result.get("firma") or "").strip()
    if not firma or _is_known(firma, _known_names()):
        return None

    lead_name = _write_lead_stub(firma, sender, subject, date)
    # Kein eigener Korrespondenz-Ordner für die allererste Mail (Sebastian,
    # 2026-08-19: nie wieder Leads/<Name>-Korrespondenz/) - Absender und
    # Betreff stehen bereits im "## Erste Nachricht"-Abschnitt des Lead-Stubs
    # oben in _write_lead_stub(). Erst eine ZWEITE Mail an diesen Lead
    # (email_indexer._match_lead-Treffer bei einem künftigen Indexer-Lauf)
    # macht daraus einen echten Kunden-Ordner.
    memory.append_to_memory(
        "KUNDE",
        f"[E-Mail-Erstkontakt] {firma} - Mail '{subject}' von {sender} am {date}",
    )
    return firma
