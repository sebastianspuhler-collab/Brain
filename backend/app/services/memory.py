"""Gedächtnis-Verwaltung: memory.md schreiben/deduplizieren + Auto-Learning per Claude.

Migriert aus _agent/brain_server.py (_append_to_memory, auto_remember,
_auto_memory_from_email, _auto_memory_from_file).
"""
import json
import re
from datetime import datetime

from app.config import get_settings
from app.services.anthropic_client import get_client, get_response_text

_CORRECTION_SIGNALS = {
    "nein", "falsch", "stimmt nicht", "das ist nicht", "eigentlich",
    "merke dir", "vergiss nicht", "das weißt du doch", "du liegst falsch",
    "nicht korrekt", "falsche zahl", "der preis ist", "kostet", "nicht in",
    "kein zugriff", "das liegt bei dir", "du hast doch", "ist doch",
}


def _is_duplicate(fakt: str, existing: str) -> bool:
    key_words = set(fakt.lower().split()[:5])
    return any(
        len(key_words & set(line.lower().split())) >= 3
        for line in existing.split("\n")
        if line.strip()
    )


def append_to_memory(kategorie: str, fakt: str) -> None:
    settings = get_settings()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n- [{ts}] {fakt.strip()}"
    content = settings.memory_path.read_text(encoding="utf-8", errors="ignore") if settings.memory_path.exists() else ""
    header = f"## {kategorie}"
    if header in content:
        content = content.replace(header, f"{header}{entry}", 1)
    else:
        content = content.rstrip() + f"\n\n{header}{entry}\n"
    settings.memory_path.write_text(content, encoding="utf-8")


def _extract_json_items(text: str) -> list[dict]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return []
    try:
        return json.loads(match.group()).get("items", [])
    except Exception:
        return []


def auto_remember(user_msg: str, assistant_msg: str) -> list[str]:
    """Sonnet extrahiert dauerhaft wichtige Fakten aus einem Chat-Austausch."""
    settings = get_settings()
    is_correction = any(sig in user_msg.lower() for sig in _CORRECTION_SIGNALS)
    prompt = f"""Du bist der Memory-Manager des Prozessia Brain.
Analysiere diesen Gesprächsaustausch und extrahiere NUR dauerhaft wichtige Informationen für Sebastian Spuhler.

{"ACHTUNG: Sebastian korrigiert etwas - diese Korrektur unbedingt als KORREKTUR-Eintrag speichern!" if is_correction else ""}

SPEICHERN - aggressiv, lieber zu viel als zu wenig:
- Korrekturen (Sebastian sagt etwas ist falsch/anders) -> KORREKTUR
- Neue Fakten: Preise, Vertragsinhalte, Deadlines, Entscheidungen -> KONTEXT
- Kundensituationen, Projektstände, neue Kontakte -> KUNDE
- Arbeitsregeln und Präferenzen von Sebastian -> REGEL
- Prozessentscheidungen, Abläufe -> PROZESS

NICHT SPEICHERN: reine Informationsabfragen ohne neuen Fakt, bereits bekannte Dinge.

Sebastian: {user_msg[:800]}

Brain: {assistant_msg[:400]}

JSON-Antwort (kein Markdown):
{{"items": [{{"kategorie": "KORREKTUR", "fakt": "präzise Aussage"}}]}}
Max 3 Items. Wenn nichts Neues: {{"items": []}}"""

    try:
        result = get_client().messages.create(
            model="claude-sonnet-5", max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        items = _extract_json_items(get_response_text(result).strip())
    except Exception:
        return []

    saved = []
    existing = settings.memory_path.read_text(encoding="utf-8", errors="ignore") if settings.memory_path.exists() else ""
    for item in items:
        kat = item.get("kategorie", "KONTEXT").upper()
        fakt = item.get("fakt", "").strip()
        if fakt and len(fakt) > 15 and not _is_duplicate(fakt, existing):
            append_to_memory(kat, fakt)
            existing += f"\n{fakt}"
            saved.append(fakt)
    return saved


def learn_from_text(source_label: str, prompt_body: str, min_len: int = 15) -> list[str]:
    """Gemeinsame Logik für Auto-Learning aus E-Mails und neuen Vault-Dateien."""
    settings = get_settings()
    try:
        result = get_client().messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=500,
            messages=[{"role": "user", "content": prompt_body}],
        )
        items = _extract_json_items(get_response_text(result).strip())
    except Exception:
        return []

    saved = []
    existing = settings.memory_path.read_text(encoding="utf-8", errors="ignore") if settings.memory_path.exists() else ""
    for item in items[:5]:
        kat = item.get("kategorie", "KONTEXT").upper()
        fakt = item.get("fakt", "").strip()
        if fakt and len(fakt) > min_len and not _is_duplicate(fakt, existing):
            append_to_memory(kat, f"[{source_label}] {fakt}")
            existing += f"\n{fakt}"
            saved.append(fakt)
    return saved


def learn_from_email(sender: str, subject: str, body: str) -> list[str]:
    prompt = f"""Analysiere diese E-Mail für Sebastian Spuhler (Prozessia GbR) und extrahiere wichtige Informationen.

SPEICHERN: Aufträge, Preise, Deadlines, Kundenwünsche, Zusagen, Absagen, Namen+Rollen, nächste Schritte, Entscheidungen
NICHT SPEICHERN: reine Bestätigungen ohne neuen Inhalt, Kalendereinladungen ohne Kontext

Von: {sender}
Betreff: {subject}
Inhalt: {body[:1000]}

NUR JSON (kein Markdown):
{{"items": [{{"kategorie": "KONTEXT", "fakt": "präzise Aussage auf Deutsch mit Datum falls vorhanden"}}]}}
Kategorien: KONTEXT, PROZESS, KORREKTUR, KUNDE
Wenn nichts Neues: {{"items": []}}"""
    return learn_from_text(subject[:40], prompt, min_len=10)


def learn_from_file(rel_path: str, content: str) -> list[str]:
    from pathlib import Path

    prompt = f"""Eine neue Datei wurde in den Prozessia-Vault aufgenommen. Extrahiere dauerhaft wichtige Fakten für Sebastian Spuhler.

SPEICHERN: Kundendaten, Preise, Vertragsdetails, Deadlines, Anforderungen, Entscheidungen, Projektstatus
NICHT SPEICHERN: Formatierungsinfos, allgemeine Erklärungen, offensichtliche Standardinhalte

Datei: {rel_path}
Inhalt (Auszug):
{content[:1500]}

NUR JSON:
{{"items": [{{"kategorie": "KONTEXT", "fakt": "präziser Fakt auf Deutsch"}}]}}
Kategorien: KONTEXT, KUNDE, PROZESS, KORREKTUR
Max 5 Items. Wenn nichts Neues: {{"items": []}}"""
    return learn_from_text(Path(rel_path).name, prompt, min_len=15)


def is_important_email(sender: str, subject: str, body: str) -> bool:
    """Filtert nur offensichtlichen Spam/Newsletter raus - lernt sonst von allem."""
    combined = (sender + " " + subject + " " + body[:200]).lower()
    spam = {
        "newsletter", "unsubscribe", "abmelden", "noreply", "no-reply",
        "donotreply", "marketing@", "info@mailchimp", "notification",
    }
    return not any(s in combined for s in spam)
