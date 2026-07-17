"""E-Mail-Indexer: neue Gmail-Nachrichten als Markdown cachen + in FAISS aufnehmen.
Migriert aus brain_server.py (index_new_emails, _email_indexer_loop)."""
import json
import re
import threading

from app.config import get_settings
from app.services import gmail_client, memory, rag


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

        date_slug = re.sub(r"[^\d]", "", date[:10]) or "00000000"
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
