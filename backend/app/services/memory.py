"""Gedächtnis-Verwaltung: memory.md schreiben/deduplizieren + Auto-Learning per Claude.

Migriert aus _agent/brain_server.py (_append_to_memory, auto_remember,
_auto_memory_from_email, _auto_memory_from_file).
"""
import json
import re
from datetime import datetime

from app.config import get_settings
from app.constants import Models
from app.services.anthropic_client import complete_json

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


def _existing_categories(content: str) -> list[str]:
    return re.findall(r"(?m)^## (.+)$", content)


def _normalize_category(name: str) -> str:
    """Nur Groß/Kleinschreibung, Leerzeichen und Unterstriche egalisiert -
    bewusst KEIN Fuzzy-/Stemming-Match (Singular/Plural, Tippfehler), das
    Risiko falscher Zusammenführungen unähnlicher Kategorien wäre größer als
    der Nutzen. Fängt genau die mechanischen Varianten ab, die
    append_to_memory() vorher blind als neue Section angelegt hat."""
    return re.sub(r"[^A-ZÄÖÜ]", "", name.upper())


def _find_existing_header(kategorie: str, content: str) -> str | None:
    target = _normalize_category(kategorie)
    for existing in _existing_categories(content):
        if _normalize_category(existing) == target:
            return existing
    return None


def append_to_memory(kategorie: str, fakt: str) -> None:
    """Fügt einen Fakt unter '## {kategorie}' an - findet dabei eine
    bestehende Section mit demselben (normalisierten) Namen wieder, statt bei
    abweichender Schreibweise (Groß/Kleinschreibung, Unterstrich vs.
    Leerzeichen) eine neue Parallel-Section anzulegen. Korrigiert 2026-08-20:
    genau das ist wiederholt passiert (u.a. 'ANFORDERUNG' + 'ANFORDERUNGEN',
    'PREIS' + 'PREISE', 'NÄCHSTE_SCHRITTE' + 'NÄCHSTE SCHRITTE' liefen
    getrennt nebeneinander her) - memory.md einmalig bereinigt, dieser Fix
    verhindert das Wiederauftreten. Die Prompts in auto_remember()/
    learn_from_text() geben dem Modell zusätzlich die bestehenden
    Kategorienamen vor, damit es sie von vornherein wiederverwendet - dieser
    Normalisierungs-Fallback greift nur, wenn das trotzdem mal abweicht."""
    settings = get_settings()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n- [{ts}] {fakt.strip()}"
    content = settings.memory_path.read_text(encoding="utf-8", errors="ignore") if settings.memory_path.exists() else ""
    existing = _find_existing_header(kategorie, content)
    header = f"## {existing if existing else kategorie}"
    if existing:
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
    bestehende_kategorien = _existing_categories(
        settings.memory_path.read_text(encoding="utf-8", errors="ignore") if settings.memory_path.exists() else ""
    )
    prompt = f"""Du bist der Memory-Manager des Prozessia Brain.
Analysiere diesen Gesprächsaustausch und extrahiere NUR dauerhaft wichtige Informationen für Sebastian Spuhler.

{"ACHTUNG: Sebastian korrigiert etwas - diese Korrektur unbedingt als KORREKTUR-Eintrag speichern!" if is_correction else ""}

SPEICHERN - aggressiv, lieber zu viel als zu wenig:
- Korrekturen (Sebastian sagt etwas ist falsch/anders) -> KORREKTUR
- Neue Fakten: Preise, Vertragsinhalte, Deadlines, Entscheidungen -> KONTEXT
- Kundensituationen, Projektstände, neue Kontakte -> KUNDE
- Arbeitsregeln und Präferenzen von Sebastian -> REGEL
- Prozessentscheidungen, Abläufe -> PROZESS

WICHTIG zur Kategorie-Wahl: passt eine bereits bestehende Kategorie
(exakte Schreibweise übernehmen, auch Singular/Plural), diese verwenden statt
eine ähnliche neue zu erfinden - jede abweichende Schreibweise legt sonst
eine eigene Parallel-Section an.
{f"Bestehende Kategorien: {', '.join(bestehende_kategorien)}" if bestehende_kategorien else ""}

NICHT SPEICHERN: reine Informationsabfragen ohne neuen Fakt, bereits bekannte Dinge.

Sebastian: {user_msg[:800]}

Brain: {assistant_msg[:400]}

JSON-Antwort (kein Markdown):
{{"items": [{{"kategorie": "KORREKTUR", "fakt": "präzise Aussage"}}]}}
Max 3 Items. Wenn nichts Neues: {{"items": []}}"""

    try:
        # thinking deaktiviert: sonst kann das knappe max_tokens-Budget fürs
        # Nachdenken draufgehen und die JSON-Antwort abgeschnitten zurückkommen
        # (dieselbe Ursache wie der classify()-Bug 2026-07-17) - hier besonders
        # tückisch, weil das lautlos bei JEDER Chat-Nachricht passiert und einfach
        # nichts gespeichert wird, ohne dass irgendwas auffällt.
        raw = complete_json(prompt, model=Models.SONNET, max_tokens=300)
        items = _extract_json_items(raw.strip())
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
    bestehende_kategorien = _existing_categories(
        settings.memory_path.read_text(encoding="utf-8", errors="ignore") if settings.memory_path.exists() else ""
    )
    if bestehende_kategorien:
        # Ergänzung 2026-08-20: die eigenen "Kategorien: ..."-Hinweise in
        # learn_from_email()/learn_from_file() unten nennen nur eine grobe
        # Kernauswahl - das Modell hat trotzdem wiederholt eigene, ähnliche
        # Kategorienamen erfunden (ANFORDERUNG/ANFORDERUNGEN, PREIS/PREISE
        # etc. liefen als getrennte Sections nebeneinander her). Die
        # tatsächlich vorhandenen Kategorien hier zusätzlich mitgeben, damit
        # exakte Wiederverwendung wahrscheinlicher wird.
        prompt_body += (
            f"\n\nBestehende Kategorien in memory.md (exakte Schreibweise wiederverwenden, "
            f"auch wenn sie nicht oben in der Liste steht): {', '.join(bestehende_kategorien)}"
        )
    try:
        raw = complete_json(prompt_body, model=Models.HAIKU, max_tokens=500)
        items = _extract_json_items(raw.strip())
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
