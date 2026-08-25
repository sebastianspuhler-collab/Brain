"""Automatische Termin-Erinnerungsmails (Sebastian, 2026-08-16): vorher schickte
er Erinnerungen an externe Meeting-Teilnehmer immer von Hand, kurz vorher oder
morgens ("kurze Erinnerung an unseren Termin..."). Legt jetzt automatisch einen
Gmail-Entwurf an, sobald ein Kalendertermin mit externen Teilnehmern in
REMINDER_LEAD_MINUTES bevorsteht - Sebastian prüft/schickt den Entwurf selbst,
es wird NICHTS automatisch versendet (2026-08-16 explizit so entschieden).

Anrede/Nachname wird NICHT vom LLM erfunden - das muss laut Sebastian
zuverlässig stimmen. Reihenfolge: 1) bereits bekannter Kontakt im Vault
(Kunden/Leads, Volltextsuche nach der E-Mail-Adresse), 2) Graph-Anzeigename,
falls er wie ein echter "Vorname Nachname" aussieht, 3) aus dem Lokalteil der
E-Mail-Adresse abgeleitet (Sebastian: "das kann man anhand der emailadresse
erkennen meistens"). Das LLM bekommt Vor-/Nachname als FESTE Vorgabe und
entscheidet nur noch Anrede (Herr/Frau) und formuliert den Text im Stil der
echten Beispiel-Mails unten.
"""
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import get_settings
from app.constants import Models
from app.services import gmail_client, outlook_client
from app.services.anthropic_client import complete_json
from app.services.calendar_lead_service import INTERNAL_DOMAIN, _external_attendees

REMINDER_LEAD_MINUTES = 60
BERLIN = ZoneInfo("Europe/Berlin")

# Echte Beispiele aus Sebastians gesendeten Mails (Gmail, Juli/Aug 2026) - als
# Few-Shot-Vorlage fürs LLM, damit Ton/Länge/Struktur exakt seinem Stil
# entsprechen statt einer generischen KI-Mail.
_STYLE_EXAMPLES = """Beispiel 1 (Betreff: "Erinnerung: unser Termin heute um 9 Uhr"):
Guten Morgen Herr Haller,

kurze Erinnerung an unseren Termin heute um 9:00 Uhr (Teams-Meeting "Prozessia X Schauenberg"). Ich freue mich auf den Austausch.

Bis gleich!

Mit freundlichen Grüßen

Beispiel 2 (Betreff: "Unser Termin"):
Hallo Herr Bhawar,

Anbei eine kurze Erinnerung an unser Meeting in ca. 1 Stunde:
https://teams.microsoft.com/meet/358720630743689?p=nvo0EscZq6w5HSNsyV

Ich freue mich auf den Austausch!

VG

Beispiel 3 (Betreff: "Unser Termin", zwei Teilnehmer):
Guten Tag Herr Biebl, Guten Tag Herr Lenbner,

nochmal vorsorglich ein kleiner Reminder an unser Meeting in wenigen Minuten:
https://teams.microsoft.com/meet/32296693169524?p=OgcZjHMnofcCG0dwFA

Ich freue mich auf den Austausch.

Beste Grüße"""


def _cache_path():
    return get_settings().agent_dir / "logs" / "reminder_cache.json"


def _load_cache() -> set[str]:
    path = _cache_path()
    try:
        return set(json.loads(path.read_text(encoding="utf-8"))) if path.exists() else set()
    except Exception:
        return set()


def _save_cache(ids: set[str]) -> None:
    path = _cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(ids), ensure_ascii=False, indent=2), encoding="utf-8")


def _event_start(event: dict) -> datetime | None:
    start = event.get("start") or {}
    dt_str = (start.get("dateTime") or "").split(".")[0]
    if not dt_str:
        return None
    tz_name = start.get("timeZone") or "Europe/Berlin"
    try:
        return datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=ZoneInfo(tz_name))
    except Exception:
        return None


def _teams_link(event: dict) -> str:
    """Sebastian verlinkt in seinen Mails immer die kurze teams.microsoft.com/meet/-
    Form aus der Einladung (bodyPreview), nicht die lange onlineMeeting.joinUrl -
    also genau diese extrahieren, nicht das Graph-Feld direkt nehmen."""
    body = event.get("bodyPreview") or ""
    m = re.search(r"https://teams\.microsoft\.com/meet/\S+", body)
    if m:
        return m.group(0).rstrip(".,)")
    return ((event.get("onlineMeeting") or {}).get("joinUrl")) or ""


def _derive_name_from_email(address: str) -> tuple[str, str]:
    local = address.split("@")[0]
    parts = [p for p in re.split(r"[._\-]+", local) if p and not p.isdigit()]
    parts = [p.capitalize() for p in parts]
    if len(parts) >= 2:
        return parts[0], parts[-1]
    if parts:
        return parts[0], parts[0]
    return "", ""


_GENERIC_LOCAL_PARTS = {
    "info", "kontakt", "contact", "office", "hello", "sales", "mail",
    "team", "support", "buero", "büro", "empfang", "post",
}


def _lookup_known_contact(address: str) -> tuple[str, str] | None:
    """Volltextsuche nach der E-Mail-Adresse in Kunden/ und Leads/. Bewusst
    ENG an das tatsächlich verwendete Notiz-Format gebunden - "Vorname
    Nachname (..., email@...)" direkt gefolgt von einer schließenden Klammer
    (siehe z.B. "Dominik Nussbaumer (TopDown, dominik.nussbaumer@...)" in den
    TopDown-Meeting-Notizen) - NICHT eine lose Nähe-Suche im Fließtext: eine
    frühere, großzügigere Version davon hat live einen falschen Namen
    ("Zillmer-Elektrotechnik" + "von") statt des echten Kontakts geliefert.
    Lieber kein Treffer als ein falscher - der Nachname muss laut Sebastian
    zuverlässig stimmen."""
    settings = get_settings()
    pattern = re.compile(
        r"([A-ZÄÖÜ][a-zäöüß\-]+)\s+([A-ZÄÖÜ][a-zäöüß\-]+)\s*\([^)]{0,120}?"
        + re.escape(address) + r"[^)]{0,80}?\)",
        re.IGNORECASE,
    )
    for root_name in ("Kunden", "Leads"):
        root = settings.vault_path / root_name
        if not root.exists():
            continue
        for md_path in root.rglob("*.md"):
            try:
                text = md_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if address.lower() not in text.lower():
                continue
            m = pattern.search(text)
            if m:
                return m.group(1), m.group(2)
    return None


def resolve_contact_name(address: str, graph_name: str) -> tuple[str, str]:
    """Priorität laut Sebastian (2026-08-16): die E-Mail-Adresse selbst ist
    der zuverlässigste Indikator ("das kann man anhand der emailadresse
    erkennen meistens") - vorname.nachname@firma.de ist im B2B-Alltag die mit
    Abstand häufigste Konvention und eindeutig, anders als Freitext-Suche im
    Vault oder der oft nur die E-Mail-Adresse wiederholende Graph-Anzeigename.
    Vault-Suche/Graph-Name nur als Fallback bei generischen Adressen
    (info@, kontakt@, ...) ohne verwertbaren Vor-/Nachnamen im Lokalteil."""
    local = address.split("@")[0]
    email_guess = _derive_name_from_email(address)
    generic = local.lower() in _GENERIC_LOCAL_PARTS or len(email_guess[0]) < 2 or len(email_guess[1]) < 2
    if not generic:
        return email_guess
    known = _lookup_known_contact(address)
    if known:
        return known
    if graph_name and graph_name.strip().lower() != address.lower() and " " in graph_name:
        parts = graph_name.strip().split()
        return parts[0], parts[-1]
    return email_guess


def _generate_email(event: dict, contacts: list[tuple[str, str]], minutes_until: int, start: datetime) -> dict:
    subject_line = event.get("subject") or "Meeting"
    link = _teams_link(event)
    # Bei generischen Sammel-Adressen (info@...) liefert resolve_contact_name()
    # bewusst keinen erfundenen Namen (z.B. ("Info", "Info")) - hier auf eine
    # namenlose, aber korrekte Anrede ausweichen statt "Herr Info" zu riskieren.
    known = [(v, n) for v, n in contacts if n.lower() not in _GENERIC_LOCAL_PARTS]
    unknown_count = len(contacts) - len(known)
    namen_liste = "; ".join(f"Vorname={v}, Nachname={n}" for v, n in known) or "keine (nur generische Adresse)"
    prompt = f"""Du schreibst für Sebastian Spuhler (Geschäftsführer Prozessia GbR) eine kurze
Erinnerungsmail an externe Meeting-Teilnehmer, exakt in seinem Stil.

STIL-BEISPIELE (Ton/Länge/Struktur genau so übernehmen):
{_STYLE_EXAMPLES}

Fakten zu diesem Termin (NICHT verändern, insbesondere die Nachnamen sind fix vorgegeben):
- Teilnehmer mit bekanntem Namen: {namen_liste}
- Zusätzlich {unknown_count} Teilnehmer OHNE bekannten Namen (generische Adresse) - für
  diese KEINEN Namen erfinden, stattdessen bei der Anrede weglassen bzw. bei
  ausschließlich unbekannten Teilnehmern neutral mit "Guten Tag," (ohne Namen) grüßen.
- Meeting-Titel: {subject_line}
- Termin startet in {minutes_until} Minuten, um {start.strftime('%H:%M')} Uhr
- Teams-Link: {link or 'kein Link vorhanden - nicht erwähnen'}

Aufgaben:
1. Bestimme für JEDEN Teilnehmer "Herr" oder "Frau" (übliche deutsche
   Vornamen-Konvention, im Zweifel die wahrscheinlichere Option - NIE einen
   anderen Namen verwenden als vorgegeben).
2. Formuliere Anrede + Betreff + Mailtext wie in den Beispielen - kurz, 2-4
   Sätze, KEINE Grußformel/Signatur am Ende (wird automatisch ergänzt).
   Bei mehreren Teilnehmern alle in der Anrede nennen (siehe Beispiel 3).
   Formuliere die Zeitangabe passend zur Vorlaufzeit (z.B. "in wenigen
   Minuten" bei sehr kurzer Zeit, "in einer Stunde" bzw. "heute um {start.strftime('%H:%M')} Uhr"
   bei mehr Vorlauf).

Antworte NUR als JSON: {{"subject": "...", "body": "..."}}"""
    raw = complete_json(prompt, model=Models.SONNET, max_tokens=500).strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


def scan_and_draft_reminders() -> list[str]:
    """Prüft den Kalender auf Termine mit externen Teilnehmern innerhalb von
    REMINDER_LEAD_MINUTES und legt dafür je einen Gmail-Entwurf an. Gibt die
    Betreffzeilen der neu angelegten Entwürfe zurück (fürs Logging)."""
    if not gmail_client.is_authenticated() or not outlook_client.is_authenticated():
        return []
    cache = _load_cache()
    now = datetime.now(BERLIN)
    created = []
    for event in outlook_client.get_calendar_events(days=1):
        event_id = event.get("id")
        if not event_id or event.get("isAllDay"):
            continue
        start = _event_start(event)
        if not start:
            continue
        # Cache-Key enthaelt die Startzeit, nicht nur die Event-ID: Sebastian
        # verschiebt Termine oft, Outlook behaelt dabei aber dieselbe Event-ID
        # bei - ohne die Startzeit im Key wuerde eine bereits einmal erinnerte
        # Verschiebung fuer immer stumm uebersprungen (Live-Bug, 2026-08-25:
        # Zillmer-Termin nach mehrfacher Verschiebung nie neu erinnert, weil
        # die Event-ID vom initialen Testlauf noch im Cache stand).
        cache_key = f"{event_id}|{start.isoformat()}"
        if cache_key in cache:
            continue
        minutes_until = (start - now).total_seconds() / 60
        if not (0 <= minutes_until <= REMINDER_LEAD_MINUTES):
            continue
        externals = _external_attendees(event)
        if not externals:
            continue
        try:
            contacts = [resolve_contact_name(a["address"], a["name"]) for a in externals]
            mail = _generate_email(event, contacts, round(minutes_until), start)
            to_addr = ", ".join(a["address"] for a in externals)
            gmail_client.create_draft(to_addr, mail["subject"], mail["body"])
            created.append(mail["subject"])
        except Exception:
            continue  # nicht in den Cache aufnehmen -> nächster Poll versucht es erneut
        else:
            cache.add(cache_key)
    if created:
        _save_cache(cache)
    return created
