"""RAG-Suche über FAISS-Index. Migriert aus _agent/brain_server.py (rag_search,
_load_rag, _faiss_add_doc) und _agent/rag_index.py (build_index).

Bewusst als Singleton-Modul mit In-Memory-Index gehalten (wie im Original) —
funktioniert für 2 Nutzer mit einem Uvicorn-Worker problemlos. Bei mehreren
Workern müsste der Index extern (z.B. eigener Such-Service) gehalten werden,
siehe Migrationsplan Phase 2.

WICHTIG - dedizierter Worker-Thread (Umsetzungsplan-Memo 2026-07-16, Punkt A1):
Alle Zugriffe auf Modell/Index/BM25 (encode(), FAISS-Suche/-Mutation, BM25-
Aufbau) laufen ausschließlich auf EINEM einzigen Hintergrund-Thread (_worker_loop),
egal aus welchem Thread search()/add_document()/load()/build_full_index()
aufgerufen werden. Per Stress-Test bestätigt: schon der reine Aufruf von
SentenceTransformer.encode() aus wechselnden Python-Threads heraus (nicht
einmal zwingend gleichzeitig) kann auf diesem Rechner einen SIGSEGV auslösen -
ein bekanntes plattformspezifisches Problem von PyTorch/FAISS mit nativen
BLAS-Backends bei Cross-Thread-Aufrufen. Ein einfacher Lock reicht dagegen NICHT,
da er nur Gleichzeitigkeit verhindert, nicht den Cross-Thread-Aufruf selbst. Die
öffentliche API (search/add_document/load/build_full_index/reindex_new_files/
doc_count/is_loaded) ist unverändert - alle Aufrufer im Rest des Projekts
brauchen keine Anpassung.
"""
import json
import queue
import re
import threading
from concurrent.futures import Future
from pathlib import Path

from app.config import get_settings

_model = None
_index = None
_meta: list | None = None

_bm25 = None  # rank_bm25.BM25Okapi, gebaut über _rebuild_bm25() beim Schreiben
_bm25_size = 0  # len(_meta) beim letzten BM25-Build, zur Erkennung von Änderungen

_reranker = None  # None = noch nicht versucht, False = Laden fehlgeschlagen, sonst CrossEncoder

_worker_queue: "queue.Queue" = queue.Queue()
_worker_started = False
_worker_start_lock = threading.Lock()

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
# Mehrsprachiger Cross-Encoder für Reranking (Everlast-Video: letzte Qualitätsstufe
# einer Rack-Pipeline nach Hybrid Search). Läuft lokal wie das Embedding-Modell,
# kein neuer API-Key/Account nötig - trainiert auf mMARCO (u.a. Deutsch), passend
# zum bereits mehrsprachigen Embedding-Modell oben.
RERANK_MODEL = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
RERANK_CANDIDATES = 30  # wie viele RRF-Top-Kandidaten werden neu bewertet
SKIP_DIRS = {"_inbox", ".git", ".obsidian", "_fehler", "node_modules"}
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
RRF_K = 60  # Standardkonstante für Reciprocal Rank Fusion (üblicher Literaturwert)

_STOPWORDS = {
    "ich", "sie", "der", "die", "das", "was", "wie", "bitte", "hast", "gibt",
    "kann", "welche", "haben", "sein",
}


def _worker_loop() -> None:
    while True:
        fn, args, kwargs, fut = _worker_queue.get()
        try:
            fut.set_result(fn(*args, **kwargs))
        except BaseException as exc:  # noqa: BLE001 - Fehler muss zum Aufrufer zurück
            fut.set_exception(exc)


def _ensure_worker() -> None:
    global _worker_started
    if _worker_started:
        return
    with _worker_start_lock:
        if _worker_started:
            return
        threading.Thread(target=_worker_loop, daemon=True, name="rag-worker").start()
        _worker_started = True


def _run_on_worker(fn, *args, **kwargs):
    """Führt fn ausschließlich auf dem dedizierten RAG-Worker-Thread aus und
    blockiert bis das Ergebnis vorliegt (Aufrufer merken vom Threading nichts)."""
    _ensure_worker()
    fut: Future = Future()
    _worker_queue.put((fn, args, kwargs, fut))
    return fut.result()


def load() -> bool:
    """Lädt Modell + Index einmalig. Idempotent."""
    if _index is not None:
        return True
    return _run_on_worker(_load_impl)


def _load_impl() -> bool:
    global _model, _index, _meta
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
        _rebuild_bm25()
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


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-ZäöüÄÖÜß0-9]+", text.lower())


def _rebuild_bm25() -> None:
    """Baut den BM25-Stichwortindex über _meta[*]['content'] neu auf (Hybrid Search,
    Umsetzungsplan-Memo 2026-07-16 Punkt C2). Läuft immer schon auf dem Worker-
    Thread (aufgerufen aus _load_impl/_add_document_impl/_build_full_index_impl).

    Bewusst NUR beim Schreiben neu gebaut, nicht lazy beim Lesen in _search_impl:
    ein Stress-Test hat gezeigt, dass wiederholtes Neubauen aus dem Lese-Pfad
    heraus (bei jeder Suche während sich der Korpus durch den Inbox-Watcher
    gerade ändert) unnötig viel Zeit im Suchpfad kostet. So passiert der teure
    Neuaufbau nur einmal pro tatsächlicher Änderung."""
    global _bm25, _bm25_size
    if not _meta:
        _bm25, _bm25_size = None, 0
        return
    from rank_bm25 import BM25Okapi

    tokenized = [
        _tokenize(m.get("content", "") if isinstance(m, dict) else str(m))
        for m in _meta
    ]
    _bm25 = BM25Okapi(tokenized)
    _bm25_size = len(_meta)


def _rrf_fuse(rank_lists: list[list[int]], k: int = RRF_K) -> dict[int, float]:
    """Reciprocal Rank Fusion: kombiniert mehrere Rankings (Listen von Doc-Indizes,
    beste zuerst) zu einem gemeinsamen Score pro Doc-Index (höher = besser)."""
    scores: dict[int, float] = {}
    for ranked in rank_lists:
        for rank, idx in enumerate(ranked):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + rank + 1)
    return scores


def _get_reranker():
    """Lädt den Cross-Encoder lazy beim ersten Gebrauch (läuft immer schon auf
    dem RAG-Worker-Thread, da nur aus _search_impl heraus aufgerufen). Gibt None
    zurück, wenn das Laden fehlschlägt (z.B. kein Internetzugriff beim ersten
    Start) - Reranking wird dann übersprungen, kein Fehler für den Aufrufer."""
    global _reranker
    if _reranker is None:
        try:
            from sentence_transformers import CrossEncoder

            _reranker = CrossEncoder(RERANK_MODEL)
        except Exception:
            _reranker = False
    return _reranker or None


def _rerank(query: str, snippets: list[tuple[float, str, str]]) -> list[tuple[float, str, str]]:
    """Letzte Qualitätsstufe nach Hybrid Search (Everlast-Video): ein
    Cross-Encoder bewertet Frage+Chunk gemeinsam (präziser als reine
    Embedding-Ähnlichkeit, weil er beide Texte zusammen statt getrennt liest).
    Nur auf die RRF-besten RERANK_CANDIDATES Kandidaten angewandt, der Rest
    bleibt unangetastet dahinter. Fällt lautlos auf die unveränderte
    RRF-Reihenfolge zurück, wenn kein Reranking-Modell verfügbar ist."""
    reranker = _get_reranker()
    if reranker is None or not snippets:
        return snippets
    candidates = snippets[:RERANK_CANDIDATES]
    rest = snippets[RERANK_CANDIDATES:]
    try:
        pairs = [(query, content) for _, _, content in candidates]
        rerank_scores = reranker.predict(pairs)
        reranked = sorted(
            ((float(rs), path, content) for rs, (_, path, content) in zip(rerank_scores, candidates)),
            key=lambda x: x[0],
            reverse=True,
        )
        # Scores der Reranking-Kandidaten durch die Reranker-Scores ersetzt (andere
        # Skala als RRF, aber konsistent mit der jetzt tatsächlich verwendeten
        # Reihenfolge), der unangetastete Rest behält seine RRF-Scores.
        return reranked + rest
    except Exception:
        return snippets


def search(query: str, k: int = 15) -> str:
    """Hybrid Search: semantische FAISS-Suche + BM25-Stichwortsuche, kombiniert per
    Reciprocal Rank Fusion. Multi-Query (Hauptfrage + extrahierte Entitäten),
    Kunden/Email-Boost. Läuft komplett auf dem dedizierten RAG-Worker-Thread.

    Behebt nebenbei einen Sortier-Bug der Vorgängerversion: dort wurden die
    FAISS-Scores (höher = ähnlicher, absteigend von FAISS geliefert) aufsteigend
    sortiert und die ersten 15 genommen - das lieferte bevorzugt die SCHLECHTESTEN
    Treffer aus dem Kandidatenpool statt der besten (nur zufällig kompensiert durch
    den ebenfalls invertierten Kunden/Email-Boost-Faktor <1). Jetzt: alle Scores
    sind konsistent "höher = besser", absteigend sortiert, Boost multipliziert
    entsprechend mit einem Faktor >1.
    """
    if _index is None or _model is None:
        return ""
    error, snippets = _run_on_worker(_search_impl, query, k)
    return "" if error else _format_snippets(snippets)


def search_with_sources(
    query: str, k: int = 15, path_prefixes: tuple[str, ...] | None = None
) -> tuple[str, list[dict]]:
    """Wie search(), liefert zusätzlich eine strukturierte Quellenliste für die UI
    (Umsetzungsplan-Memo 2026-07-16, Punkt D1) - z.B. für anklickbare Quellen-Chips
    im Chat. Reine Ergänzung: search() bleibt unverändert für bestehende Aufrufer,
    diese Funktion teilt sich intern nur dieselbe Suchlogik (_search_impl).

    path_prefixes (optional, Punkt D2 - eigene Agenten mit Ordner-Filter):
    wenn gesetzt, werden nur Treffer berücksichtigt, deren Pfad mit einem der
    Präfixe beginnt. Ohne path_prefixes (Standard) unverändertes Verhalten."""
    if _index is None or _model is None:
        return "", []
    error, snippets = _run_on_worker(_search_impl, query, k, path_prefixes)
    if error:
        return "", []
    sources = []
    seen_paths: set[str] = set()
    for score, path, _content in snippets[:15]:
        if path in seen_paths:
            continue
        seen_paths.add(path)
        sources.append({"path": path, "score": round(score, 3)})
    return _format_snippets(snippets), sources[:8]


def _format_snippets(snippets: list[tuple[float, str, str]]) -> str:
    return "\n\n".join(f"[{p}]\n{c}" for _, p, c in snippets[:15])


def _search_impl(
    query: str, k: int, path_prefixes: tuple[str, ...] | None = None
) -> tuple[bool, list[tuple[float, str, str]]]:
    """Rückgabe: (error, snippets) - snippets bereits nach Score absteigend
    sortiert, error=True bei einer Exception (Aufrufer bekommt dann [])."""
    try:
        import numpy as np

        settings = get_settings()
        queries = [query] + _extract_entities(query)

        # Bei aktivem Ordner-Filter (eigene Agenten, Punkt D2) reicht ein Top-k
        # aus dem GESAMTEN Korpus nicht: ein kleiner Kundenordner (wenige
        # Dokumente unter Tausenden) taucht in den global besten 15 Treffern
        # oft gar nicht auf, dann käme ohne diese Erweiterung fälschlich ein
        # leeres Ergebnis zurück, obwohl im gefilterten Ordner passende
        # Dokumente existieren (empirisch nachgestellt: generische Frage ohne
        # Kundennamen + Ordner-Filter auf einen kleinen Kunden -> 0 Treffer).
        # Deshalb hier deutlich mehr Kandidaten aus FAISS/BM25 holen, bevor
        # gefiltert wird - der Corpus ist klein genug (~1500 Chunks aktuell),
        # dass das keine spürbaren Kosten verursacht.
        retrieve_k = min(len(_meta), 500) if path_prefixes else k

        seen: set[int] = set()
        snippets: list[tuple[float, str, str]] = []
        for q in queries:
            vec = _model.encode([q]).astype(np.float32)
            _, indices = _index.search(vec, retrieve_k)
            semantic_rank = [int(i) for i in indices[0] if 0 <= i < len(_meta)]

            bm25_rank: list[int] = []
            if _bm25 is not None:
                bm25_scores = _bm25.get_scores(_tokenize(q))
                top = np.argsort(bm25_scores)[::-1][:retrieve_k]
                bm25_rank = [int(i) for i in top if bm25_scores[i] > 0]

            fused = _rrf_fuse([semantic_rank, bm25_rank])
            for idx, score in fused.items():
                if idx in seen:
                    continue
                seen.add(idx)
                m = _meta[idx]
                path = m.get("path", "") if isinstance(m, dict) else str(m)
                if path_prefixes and not any(path.startswith(p) for p in path_prefixes):
                    continue
                try:
                    content = (settings.vault_path / path).read_text(encoding="utf-8", errors="ignore")[:1500]
                except Exception:
                    content = m.get("content", "") if isinstance(m, dict) else ""
                if not content:
                    continue
                if "Kunden/" in path:
                    score *= 1.25
                if "email_cache/" in path:
                    score *= 1.14
                snippets.append((score, path, content))

        snippets.sort(key=lambda x: x[0], reverse=True)
        snippets = _rerank(query, snippets)
        return False, snippets
    except Exception:
        return True, []


def add_document(rel_path: str, content: str) -> None:
    """Inkrementelles Hinzufügen EINER Datei zum Index (Disk-Write + BM25-Rebuild
    sofort). Für Einzelfälle gedacht. Werden mehrere Dateien am Stück hinzugefügt
    (Inbox-Batch, E-Mail-Deep-Scan mit bis zu 500 Mails) - siehe
    add_documents_batch() weiter unten, das erspart N-1 überflüssige BM25-
    Rebuilds und Festplatten-Schreibvorgänge."""
    if _index is None or _model is None:
        return
    _run_on_worker(_add_document_impl, rel_path, content)


def _add_document_impl(rel_path: str, content: str) -> None:
    try:
        import numpy as np
        import faiss as _faiss

        settings = get_settings()
        text = content[:1500]
        vec = _model.encode([text]).astype(np.float32)
        _index.add(vec)
        _meta.append({"path": rel_path, "content": text})
        _faiss.write_index(_index, str(settings.rag_index_path))
        settings.rag_meta_path.write_text(
            json.dumps(_meta, ensure_ascii=False), encoding="utf-8"
        )
        _rebuild_bm25()
    except Exception:
        pass


def add_documents_batch(items: list[tuple[str, str]]) -> None:
    """Fügt mehrere Dateien in einem Rutsch hinzu - EIN Disk-Write, EIN
    BM25-Rebuild statt einem pro Datei.

    Warum das wichtig ist: ein BM25-Rebuild dauert auf dem aktuellen Vault
    (~1500 Chunks) schon ~280ms und wächst mit der Vault-Größe. Der
    E-Mail-Indexer ruft beim ersten Deep-Scan bis zu 500x, der Inbox-Watcher
    bei einem größeren Batch mehrfach hintereinander auf - vorher (ein Rebuild
    PRO Datei über add_document()) hätte das den dedizierten RAG-Worker-Thread
    (auf dem auch jede Chat-Suche läuft, siehe A1) für bis zu 2+ Minuten
    blockiert und wäre dem ursprünglichen "Verbindung unterbrochen"-Symptom
    wieder sehr nahe gekommen. Diese Funktion behebt das, indem sie den
    teuren Teil (Disk-Write, BM25-Rebuild) nur einmal für den ganzen Batch
    ausführt, nicht pro Einzeldatei."""
    if _index is None or _model is None or not items:
        return
    _run_on_worker(_add_documents_batch_impl, items)


def _add_documents_batch_impl(items: list[tuple[str, str]]) -> None:
    import numpy as np
    import faiss as _faiss

    settings = get_settings()
    for rel_path, content in items:
        try:
            text = content[:1500]
            vec = _model.encode([text]).astype(np.float32)
            _index.add(vec)
            _meta.append({"path": rel_path, "content": text})
        except Exception:
            continue
    try:
        _faiss.write_index(_index, str(settings.rag_index_path))
        settings.rag_meta_path.write_text(
            json.dumps(_meta, ensure_ascii=False), encoding="utf-8"
        )
        _rebuild_bm25()
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
                new_files.append((rel, content))
        except Exception:
            pass
    # Ein Rutsch statt einem add_document()-Aufruf pro Datei - siehe
    # add_documents_batch() für die Begründung (Inbox-Watcher kann mehrere
    # Dateien auf einmal finden, jede einzeln wäre ein eigener BM25-Rebuild).
    add_documents_batch(new_files)
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
    return _run_on_worker(_build_full_index_impl)


def _build_full_index_impl() -> dict:
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
    _rebuild_bm25()
    return {"documents": len(docs), "chunks": len(all_chunks), "dim": dim}
