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


def _match_customer(sender: str, subject: str, body: str) -> str | None:
    """Ordnet eine E-Mail einem bestehenden Kunden/<Name>-Ordner zu, wenn der
    Kundenname (unabhängig von Groß-/Kleinschreibung und Trennzeichen) im
    Absender, Betreff oder Anfang des Inhalts auftaucht. Rein deterministisch
    (kein API-Call) - läuft für jede einzelne E-Mail, muss also kostenlos sein.

    Warum das nötig ist: bisher landeten E-Mails nur im generischen
    _agent/email_cache/, ohne Bezug zu Kunden/<Name>/ - dadurch tauchten sie
    weder im Datei-Browser des Kunden noch in kundenspezifischer RAG-Suche
    (path_prefixes) auf, obwohl die Beziehung (Absenderdomain, Betreff) längst
    erkennbar war."""
    names = classify.list_customer_names()
    if not names:
        return None
    haystack = _normalize(f"{sender} {subject} {body[:500]}")
    for name in names:
        needle = _normalize(name.replace("_", " "))
        if len(needle) >= 3 and needle in haystack:
            return name
    return None


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
    date_slug = _date_slug(date)
    safe_sub = re.sub(r"[^\w\s-]", "", subject)[:40].strip().replace(" ", "-") or "kein-betreff"
    filename = f"{date_slug[:4]}-{date_slug[4:6]}-{date_slug[6:8]}-Email-{eid[:8]}-{safe_sub}.md"
    path = dok_dir / filename
    if path.exists():
        return False
    path.write_text(
        f"---\ntype: email-korrespondenz\nkunde: {customer}\nvon: {sender}\n"
        f"betreff: {subject}\ndatum: {date}\n---\n\n# {subject}\n\n"
        f"**Von:** {sender}\n**Datum:** {date}\n\n{body}",
        encoding="utf-8",
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
