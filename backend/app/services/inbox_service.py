"""Gemeinsame Inbox-Verarbeitung, geteilt zwischen /api/upload (inbox.py) und
/api/chat/attach (chat.py) - beide sollen Dateien identisch klassifizieren,
ablegen und in den RAG-Index aufnehmen. Vorher in inbox.py als private
Funktion, jetzt hier, damit chat.py sie ohne Router-zu-Router-Import nutzen
kann (2026-07-28: Transkript-Anhänge im Chat landen jetzt auch in der Inbox)."""
from app.services import classify, memory, rag


def run_inbox_and_reindex() -> dict:
    result = classify.run_inbox()
    new_files = rag.reindex_new_files()
    for rel, content in new_files:
        memory.learn_from_file(rel, content)
    result["new_indexed"] = len(new_files)
    return result
