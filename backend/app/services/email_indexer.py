"""E-Mail-Indexer: neue Gmail-Nachrichten als Markdown cachen + in FAISS aufnehmen.
Migriert aus brain_server.py (index_new_emails, _email_indexer_loop)."""
import json
import re
import threading
from email.utils import parsedate_to_datetime

from app.config import get_settings
from app.services import classify, gmail_client, memory, rag


def _date_slug(date: str) -> str:
    """YYYYMMDD aus dem Gmail-Date-Header. Der Header kommt im RFC822-Format
    ("Tue, 07 Jul 2026 17:13:42 +0000"), ein naives date[:10] liefert daher
    Datumsmüll statt eines echten Datums (z.B. nur "07") - das fiel bisher nicht
    auf, weil niemand die email_cache-Dateinamen nach Datum auswertet, ist aber
    fatal für die Kunden-Korrespondenz-Notizen, deren Datumspräfix vom
    Dashboard für die Aktivitäts-Ampel gelesen wird."""
    try:
        return parsedate_to_datetime(date).strftime("%Y%m%d")
    except Exception:
        digits = re.sub(r"[^\d]", "", date[:10])
        return digits if len(digits) == 8 else "00000000"


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _date_iso(date: str) -> str:
    """ISO-Datum (YYYY-MM-DD) aus dem RFC822-Date-Header, leer bei Parse-Fehler."""
    try:
        return parsedate_to_datetime(date).strftime("%Y-%m-%d")
    except Exception:
        return ""


def _match_customer(sender: str, subject: str, body: str) -> str | None:
    """Ordnet eine E-Mail einem bestehenden Kunden/<Name>-Ordner zu, wenn der
    Kundenname (unabhängig von Groß-/Kleinschreibung und Trennzeichen) im
    Absender, Betreff oder Anfang des Inhalts auftaucht. Rein deterministisch
    (kein API-Call) - läuft für jede einzelne E-Mail, muss also kostenlos sein.

    Warum das nötig ist: bisher landeten E-Mails nur im generischen
    _agent/email_cache/, ohne Bezug zu Kunden/<Name>/ - dadurch tauchten sie
    weder im Datei-Browser des Kunden noch in kundenspezifischer RAG-Suche
    (path_prefixes) auf, obwohl die Beziehung (Absenderdomain, Betreff) längst
    erkennbar war.

    Mindestlänge 6 statt 3 (Sebastian, 2026-07-20): _normalize() entfernt
    JEDE Trennung (Leerzeichen, Punkte), der Haystack ist also ein einziger
    durchgehender String - Wortgrenzen lassen sich darin nicht mehr sinnvoll
    prüfen. Eine Spam-Mail mit "tpg" irgendwo im Fließtext landete deshalb im
    echten Kunden-Ordner "TPG" (3 Zeichen). Kurze Namen/Abkürzungen matchen
    über diese Funktion jetzt bewusst gar nicht mehr - lieber eine
    Korrespondenz landet nur im generischen Cache, als dass sie einen
    falschen Kunden verschmutzt."""
    names = classify.list_customer_names()
    if not names:
        return None
    haystack = _normalize(f"{sender} {subject} {body[:500]}")
    for name in names:
        needle = _normalize(name.replace("_", " "))
        if len(needle) >= 6 and needle in haystack:
            return name
    return None


def _match_lead(sender: str, subject: str, body: str) -> str | None:
    """Wie _match_customer, aber gegen Leads/ statt Kunden/ - ein Interessent
    hat noch keinen Kundenordner, soll aber genauso von einlaufender
    Korrespondenz profitieren (Sebastian, 2026-07-21: die KI soll den
    aktuellen Stand auch aus E-Mails ableiten, nicht nur aus dem einmaligen
    Erstgesprächs-Protokoll). Nur versucht, wenn kein Kunde gematcht hat -
    ein Name sollte nicht gleichzeitig Kunde und Lead sein."""
    names = classify.list_lead_names()
    if not names:
        return None
    haystack = _normalize(f"{sender} {subject} {body[:500]}")
    for name in names:
        needle = _normalize(name.replace("_", " ").replace("-", " "))
        if len(needle) >= 6 and needle in haystack:
            return name
    return None


_ZUSAMMENFASSUNG_MAX_CHARS = 600


def _korrespondenz_markdown(
    bezug_feld: str, bezug_wert: str, sender: str, subject: str, date: str, body: str
) -> str:
    """Gemeinsames Format für Kunden- und Lead-Korrespondenznotizen.

    Vorher stand im Frontmatter das RFC822-Rohdatum ("Tue, 14 Jul 2026 ...")
    statt ISO, und es gab keine "## Zusammenfassung"-Sektion - dadurch hat
    kunden_status_service._lies_dokument() (Regex auf "^datum:\\s*JJJJ-MM-TT"
    bzw. "## Zusammenfassung") beides nie gefunden: kein Datum für die
    Chronologie-Sortierung, kein Inhalt für die LLM-Synthese. Die KI hat
    E-Mail-Korrespondenz beim "Aktueller Stand" dadurch faktisch nie gesehen,
    obwohl die Dateien am richtigen Ort lagen (Sebastian, 2026-07-21). Eine
    gekürzte Klartext-Zusammenfassung statt eines eigenen LLM-Calls reicht für
    Korrespondenznotizen dieser Länge und kostet nichts zusätzlich; der volle
    Text bleibt darunter für Datei-Browser/RAG erhalten."""
    zusammenfassung = body[:_ZUSAMMENFASSUNG_MAX_CHARS].strip() or "(kein Inhalt)"
    if len(body) > _ZUSAMMENFASSUNG_MAX_CHARS:
        zusammenfassung += "…"
    return (
        f"---\ntype: email-korrespondenz\n{bezug_feld}: {bezug_wert}\nvon: {sender}\n"
        f"betreff: {subject}\ndatum: {_date_iso(date)}\ndatum_email: {date}\n---\n\n"
        f"# {subject}\n\n**Von:** {sender}\n**Datum:** {date}\n\n"
        f"## Zusammenfassung\n{zusammenfassung}\n\n## Volltext\n{body}"
    )


def _korrespondenz_filename(date: str, eid: str, subject: str) -> str:
    date_slug = _date_slug(date)
    safe_sub = re.sub(r"[^\w\s-]", "", subject)[:40].strip().replace(" ", "-") or "kein-betreff"
    return f"{date_slug[:4]}-{date_slug[4:6]}-{date_slug[6:8]}-Email-{eid[:8]}-{safe_sub}.md"


def _write_customer_correspondence(
    customer: str, eid: str, sender: str, subject: str, date: str, body: str
) -> bool:
    """Schreibt eine kurze Korrespondenz-Notiz in Kunden/<Name>/Dokumente/ - selbe
    Zielordner-Konvention wie bei Dokumenten-Klassifizierung (classify.py),
    damit Datei-Browser, Spaces-Vollständigkeitsscore und RAG-path_prefixes sie
    genauso behandeln wie jede andere Kundendatei."""
    settings = get_settings()
    dok_dir = settings.vault_path / "Kunden" / customer / "Dokumente"
    dok_dir.mkdir(parents=True, exist_ok=True)
    path = dok_dir / _korrespondenz_filename(date, eid, subject)
    if path.exists():
        return False
    path.write_text(
        _korrespondenz_markdown("kunde", customer, sender, subject, date, body), encoding="utf-8"
    )
    return True


def _write_lead_correspondence(
    lead: str, eid: str, sender: str, subject: str, date: str, body: str
) -> bool:
    """Wie _write_customer_correspondence, aber für Leads/<Name>-Korrespondenz/
    statt Kunden/<Name>/Dokumente/ - Leads sind eine einzelne .md-Datei ohne
    Unterordner, ein eigener Korrespondenz-Ordner daneben kollidiert nicht mit
    dashboard.py's nicht-rekursivem leads_dir.glob("*.md") (taucht dort nicht
    als eigener Lead auf) und wird von kunden_status_service._sammle_dokumente()
    zusätzlich zur Lead-Datei gelesen."""
    settings = get_settings()
    korr_dir = settings.vault_path / "Leads" / f"{lead}-Korrespondenz"
    korr_dir.mkdir(parents=True, exist_ok=True)
    path = korr_dir / _korrespondenz_filename(date, eid, subject)
    if path.exists():
        return False
    path.write_text(
        _korrespondenz_markdown("lead", lead, sender, subject, date, body), encoding="utf-8"
    )
    return True


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    return re.sub(r"\s+", " ", text).strip()


def _indexed_ids_path():
    return get_settings().email_cache_dir / "indexed_ids.json"


def deep_scan_done_path():
    return get_settings().email_cache_dir / "deep_scan_done.flag"


def index_new_emails(deep: bool = False) -> int:
    if not gmail_client.is_authenticated() or not rag.is_loaded():
        return 0

    settings = get_settings()
    settings.email_cache_dir.mkdir(parents=True, exist_ok=True)
    ids_path = _indexed_ids_path()

    try:
        indexed = set(json.loads(ids_path.read_text(encoding="utf-8"))) if ids_path.exists() else set()
    except Exception:
        indexed = set()

    limit = 500 if deep else 50
    try:
        raw_mails = gmail_client.get_emails(top=limit)
    except Exception:
        return 0

    new_count = 0
    # Gesammelt statt einzeln über rag.add_document() - bei einem Deep-Scan mit
    # bis zu 500 Mails wäre das 500 einzelne BM25-Rebuilds im RAG-Worker-Thread
    # (auf dem auch jede Chat-Suche läuft) gewesen, siehe rag.add_documents_batch().
    new_docs: list[tuple[str, str]] = []
    for e in raw_mails:
        eid = e.get("id", "")
        if not eid or eid in indexed:
            continue

        sender = e.get("from", "")
        subject = e.get("subject", "kein Betreff")
        date = e.get("date", "")
        body = _strip_html(e.get("body", "") or e.get("snippet", ""))[:3000]

        date_slug = _date_slug(date)
        safe_sub = re.sub(r"[^\w\s-]", "", subject)[:40].strip().replace(" ", "-")
        filename = f"{date_slug}-{eid[:8]}-{safe_sub}.md"
        rel_path = f"_agent/email_cache/{filename}"
        md_content = (
            f"---\ntype: email\nid: {eid}\nfrom: {sender}\n"
            f"subject: {subject}\ndate: {date}\n---\n\n"
            f"# {subject}\n\n**Von:** {sender}\n**Datum:** {date}\n\n{body}"
        )
        (settings.email_cache_dir / filename).write_text(md_content, encoding="utf-8")
        new_docs.append((rel_path, md_content))

        customer = _match_customer(sender, subject, body)
        if customer:
            _write_customer_correspondence(customer, eid, sender, subject, date, body)
        else:
            lead = _match_lead(sender, subject, body)
            if lead:
                _write_lead_correspondence(lead, eid, sender, subject, date, body)

        if memory.is_important_email(sender, subject, body):
            threading.Thread(
                target=memory.learn_from_email, args=(sender, subject, body), daemon=True
            ).start()

        indexed.add(eid)
        new_count += 1

    rag.add_documents_batch(new_docs)

    if new_count > 0:
        ids_path.write_text(json.dumps(list(indexed)), encoding="utf-8")
    return new_count
