"""RAG-Suche über FAISS-Index. Migriert aus _agent/brain_server.py (rag_search,
_load_rag, _faiss_add_doc) und _agent/rag_index.py (build_index).

Bewusst als Singleton-Modul mit In-Memory-Index gehalten (wie im Original) —
funktioniert für 2 Nutzer mit einem Uvicorn-Worker problemlos. Bei mehreren
Workern müsste der Index extern (z.B. eigener Such-Service) gehalten werden,
siehe Migrationsplan Phase 2.
"""
import json
import re
import threading
from pathlib import Path

from app.config import get_settings

_model = None
_index = None
_meta: list | None = None
_lock = threading.Lock()

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
SKIP_DIRS = {"_inbox", ".git", ".obsidian", "_fehler", "node_modules"}
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

_STOPWORDS = {
    "ich", "sie", "der", "die", "das", "was", "wie", "bitte", "hast", "gibt",
    "kann", "welche", "haben", "sein",
}


def load() -> bool:
    """Lädt Modell + Index einmalig. Idempotent, threadsicher."""
    global _model, _index, _meta
    if _index is not None:
        return True
    with _lock:
        if _index is not None:
            return True
        try:
            import faiss
            from sentence_transformers import SentenceTransformer

            settings = get_settings()
            if not settings.rag_index_path.exists() or not settings.rag_meta_path.exists():
                return False
            _index = faiss.read_index(str(settings.rag_index_path))
            raw = json.loads(settings.rag_meta_path.read_text(encoding="utf-8"))
            _meta = raw if isinstance(raw, list) else list(raw.values())
            _model = SentenceTransformer(f"sentence-transformers/{MODEL_NAME}")
            return True
        except Exception:
            return False


def is_loaded() -> bool:
    return _index is not None


def doc_count() -> int:
    return len(_meta) if _meta else 0


def _extract_entities(query: str) -> list[str]:
    entities = re.findall(r"\b[A-ZÄÖÜ][a-zäöüß]{2,}\b", query)
    return [e for e in entities[:4] if e.lower() not in _STOPWORDS]


def search(query: str, k: int = 15) -> str:
    """Multi-Query-Suche: Hauptfrage + extrahierte Entitäten, Kunden/Email-Boost."""
    if _index is None or _model is None:
        return ""
    try:
        import numpy as np

        settings = get_settings()
        queries = [query] + _extract_entities(query)

        seen: set[int] = set()
        snippets: list[tuple[float, str, str]] = []
        for q in queries:
            vec = _model.encode([q]).astype(np.float32)
            distances, indices = _index.search(vec, k)
            for dist, idx in zip(distances[0], indices[0]):
                if idx < 0 or idx >= len(_meta) or idx in seen:
                    continue
                seen.add(int(idx))
                m = _meta[idx]
                path = m.get("path", "") if isinstance(m, dict) else str(m)
                try:
                    content = (settings.vault_path / path).read_text(encoding="utf-8", errors="ignore")[:1500]
                except Exception:
                    content = m.get("content", "") if isinstance(m, dict) else ""
                if not content:
                    continue
                score = float(dist)
                if "Kunden/" in path:
                    score *= 0.80
                if "email_cache/" in path:
                    score *= 0.88
                snippets.append((score, path, content))

        snippets.sort(key=lambda x: x[0])
        return "\n\n".join(f"[{p}]\n{c}" for _, p, c in snippets[:15])
    except Exception:
        return ""


def add_document(rel_path: str, content: str) -> None:
    """Inkrementelles Hinzufügen einer neuen Datei zum Index, ohne Rebuild."""
    if _index is None or _model is None:
        return
    try:
        import numpy as np
        import faiss as _faiss

        settings = get_settings()
        text = content[:1500]
        vec = _model.encode([text]).astype(np.float32)
        with _lock:
            _index.add(vec)
            _meta.append({"path": rel_path, "content": text})
            _faiss.write_index(_index, str(settings.rag_index_path))
            settings.rag_meta_path.write_text(
                json.dumps(_meta, ensure_ascii=False), encoding="utf-8"
            )
    except Exception:
        pass


def reindex_new_files() -> list[tuple[str, str]]:
    """Findet .md-Dateien im Vault, die noch nicht im Index sind, fügt sie hinzu.

    Gibt (rel_path, content) für neu hinzugefügte Dateien zurück, damit der Aufrufer
    z.B. auto-memory-Extraktion darauf anstoßen kann.
    """
    if _meta is None or _model is None:
        return []
    settings = get_settings()
    existing = {(m.get("path", "") if isinstance(m, dict) else str(m)) for m in _meta}
    new_files: list[tuple[str, str]] = []
    for md_file in sorted(settings.vault_path.rglob("*.md")):
        if any(skip in md_file.parts for skip in SKIP_DIRS):
            continue
        rel = str(md_file.relative_to(settings.vault_path))
        if rel in existing:
            continue
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")[:1500]
            if len(content) > 50:
                add_document(rel, content)
                new_files.append((rel, content))
        except Exception:
            pass
    return new_files


def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + size
        chunks.append(" ".join(words[start:end]))
        start += size - overlap
    return chunks if chunks else [text[:size]]


def build_full_index() -> dict:
    """Vollständiger Neuaufbau des Index (entspricht altem rag_index.py build_index).
    Für den einmaligen Erstlauf oder bewusstes Rebuild, nicht für den Alltagsbetrieb."""
    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer

    settings = get_settings()
    model = SentenceTransformer(f"sentence-transformers/{MODEL_NAME}")

    docs = []
    for md in sorted(settings.vault_path.rglob("*.md")):
        if any(part in SKIP_DIRS for part in md.parts):
            continue
        try:
            text = md.read_text(encoding="utf-8", errors="ignore").strip()
            if text:
                docs.append((str(md.relative_to(settings.vault_path)), text))
        except Exception:
            pass

    all_chunks: list[str] = []
    metadata: list[dict] = []
    for rel_path, text in docs:
        chunks = _chunk_text(text)
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            metadata.append({"path": rel_path, "chunk_index": i, "content": chunk[:1500]})

    embeddings = model.encode(
        all_chunks, batch_size=64, convert_to_numpy=True, normalize_embeddings=True
    )
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings.astype(np.float32))

    settings.rag_index_path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(settings.rag_index_path))
    settings.rag_meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    global _index, _meta, _model
    _index, _meta, _model = index, metadata, model
    return {"documents": len(docs), "chunks": len(all_chunks), "dim": dim}
