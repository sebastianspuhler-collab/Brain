"""Erkennt aus Kalenderterminen automatisch neue potenzielle Kunden.

Bisher wurden Kunden/Leads nur aus Dokumenten/Transkripten erkannt, die schon
im Vault liegen (classify.py) oder aus E-Mails, die zu einem BESTEHENDEN
Kunden passen (email_indexer.py). Diese Lücke: ein Erstgespräch (Teams-Termin)
mit jemandem komplett Neuem wurde vom System gar nicht bemerkt, bis irgendwann
ein Transkript hochgeladen wurde.

Sebastian: "man sollte allgemein erkennen, wann ein Erstgespräch per Teams
stattfindet" - nicht anhand eines festen Namensmusters, sondern dynamisch wie
der Rest des Systems: pro Termin entscheidet Claude, ob es sich um ein
Erstgespräch mit einem neuen Kontakt handelt (externe Teilnehmer, kein
bestehender Kunde), nicht eine feste Regel.
"""
import json
import re
from datetime import datetime

from app.config import get_settings
from app.constants import Models
from app.services import classify, memory, outlook_client
from app.services.anthropic_client import get_client, get_response_text

INTERNAL_DOMAIN = "prozessia.de"


def _cache_path():
    return get_settings().agent_dir / "logs" / "calendar_lead_cache.json"


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


def _event_date(event: dict) -> str:
    """YYYY-MM-DD aus event['start']['dateTime'] - Graph liefert start/end als
    dict ({"dateTime": ..., "timeZone": ...}), kein Freitext-String."""
    start = event.get("start") or {}
    date_time = start.get("dateTime", "") if isinstance(start, dict) else ""
    return date_time[:10] if date_time else ""


def _external_attendees(event: dict) -> list[dict]:
    result = []
    for a in event.get("attendees", []):
        info = a.get("emailAddress", {}) or {}
        addr, name = info.get("address", ""), info.get("name", "")
        if addr and INTERNAL_DOMAIN not in addr.lower():
            result.append({"name": name, "address": addr})
    return result


def normalize_name(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _known_names() -> set[str]:
    """Bereits bekannte Kunden (Kunden/-Ordner) + Leads (Dateinamen in Leads/),
    normalisiert - damit ein Termin nicht doppelt als 'neuer' Lead angelegt wird."""
    settings = get_settings()
    names = {normalize_name(n) for n in classify.list_customer_names()}
    leads_dir = settings.vault_path / "Leads"
    if leads_dir.exists():
        for f in leads_dir.glob("*.md"):
            names.add(normalize_name(re.sub(r"^\d{4}-\d{2}-\d{2}-", "", f.stem)))
    return names


def _is_known(firma: str, known: set[str]) -> bool:
    """Substring-Abgleich statt exakter Gleichheit - Claude extrahiert oft den
    vollen Firmennamen ("TPG Packaging"), während der Ordner nur die Kurzform
    ("TPG") trägt. Ohne das legt der Scan sonst Duplikate für längst bekannte
    Kunden an (live beobachtet: "TPG Packaging" wurde fälschlich als neuer
    Lead erkannt, obwohl Kunden/TPG/ bereits existiert)."""
    needle = normalize_name(firma)
    if not needle:
        return False
    return any(k and (k in needle or needle in k) for k in known)


def _classify_event(event: dict, external: list[dict]) -> dict | None:
    attendee_str = ", ".join(f"{a['name']} <{a['address']}>" for a in external)
    location = event.get("location", {})
    ort = location.get("displayName", "") if isinstance(location, dict) else ""
    prompt = f"""Du prüfst einen Kalendertermin von Sebastian Spuhler (Prozessia GbR,
KI-Agentur, Saarbrücken) auf ein mögliches ERSTGESPRÄCH mit einem neuen, noch
unbekannten potenziellen Kunden/Lead.

Termin: {event.get("subject", "")}
Ort/Format: {ort}
Externe Teilnehmer: {attendee_str}
Beschreibung: {(event.get("bodyPreview") or "")[:300]}

Ist das ein Erstgespräch mit einem NEUEN potenziellen Kunden (nicht ein bereits
bestehender Kunde, kein internes Meeting, kein Recruiting-/Bewerbungsgespräch,
keine private Verabredung, kein Webinar/Massentermin)? Wenn ja, extrahiere die
Firma (falls keine erkennbar: den Namen der Person).

NUR JSON:
{{"ist_erstgespraech": true, "firma": "Firmenname oder Personenname"}}
Wenn nein oder unklar: {{"ist_erstgespraech": false}}"""
    try:
        result = get_client().messages.create(
            model=Models.HAIKU, max_tokens=200,
            thinking={"type": "disabled"},
            messages=[{"role": "user", "content": prompt}],
        )
        text = get_response_text(result).strip()
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        data = json.loads(match.group())
        return data if data.get("ist_erstgespraech") else None
    except Exception:
        return None


def _write_lead_stub(firma: str, event: dict, external: list[dict]) -> None:
    settings = get_settings()
    leads_dir = settings.vault_path / "Leads"
    leads_dir.mkdir(parents=True, exist_ok=True)
    datum = _event_date(event) or datetime.now().strftime("%Y-%m-%d")
    safe_name = re.sub(r"[^\w\s-]", "", firma)[:40].strip().replace(" ", "-")
    path = leads_dir / f"{datum}-{safe_name}.md"
    if path.exists():
        return
    teilnehmer = "\n".join(f"- {a['name'] or a['address']} ({a['address']})" for a in external)
    path.write_text(
        f"""---
tags:
  - Lead
  - Kalender-Erstgespraech
quelle: Kalender
datum: {datum}
kategorie: Lead
---

# {firma}

## Zusammenfassung
Automatisch aus einem Kalendertermin erkanntes Erstgespräch mit einem neuen
potenziellen Kunden. Noch kein Transkript/Dokument vorhanden - diese Notiz
ist der erste Anhaltspunkt, wird ergänzt sobald mehr Material eintrifft.

## Termin
{event.get("subject", "")} ({datum})

## Teilnehmer
{teilnehmer}
""",
        encoding="utf-8",
    )


def scan_for_new_leads() -> list[str]:
    """Prüft die nächsten 45 Tage Kalender auf neue Erstgespräche, legt bei
    Treffern eine Lead-Notiz in Leads/ an. Gibt die Namen der neu erkannten
    Leads zurück (für Logging)."""
    if not outlook_client.is_authenticated():
        return []

    cache = _load_cache()
    known = _known_names()
    found = []

    try:
        raw = outlook_client.get_calendar_events(days=45)
    except Exception:
        return []

    for event in raw:
        eid = event.get("id", "")
        if not eid or eid in cache:
            continue
        cache.add(eid)

        external = _external_attendees(event)
        if not external:
            continue

        result = _classify_event(event, external)
        if not result:
            continue
        firma = result.get("firma", "").strip()
        if not firma or _is_known(firma, known):
            continue

        _write_lead_stub(firma, event, external)
        memory.append_to_memory(
            "KUNDE",
            f"[Kalender-Erstgespräch] {firma} - Termin '{event.get('subject', '')}' "
            f"am {_event_date(event)} mit "
            f"{', '.join(a['name'] or a['address'] for a in external)}",
        )
        known.add(normalize_name(firma))
        found.append(firma)

    _save_cache(cache)
    return found
