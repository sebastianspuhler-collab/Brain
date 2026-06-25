"""
RAG Index für Prozessia Second Brain
Indiziert alle Vault-Markdown-Dateien mit FAISS + sentence-transformers.

Ausführen:
    python3 _agent/rag_index.py          # Vollständiger Re-Index
    python3 _agent/rag_index.py --check  # Nur Status ausgeben
"""

import json
import sys
import time
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

VAULT = Path.home() / "Documents" / "Prozessia-Brain"
INDEX_PATH = VAULT / "_agent" / "vault.index"
META_PATH = VAULT / "_agent" / "vault_metadata.json"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

SKIP_DIRS = {"_inbox", ".git", ".obsidian"}

# Maximale Zeichenlänge pro Chunk
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


def load_model():
    return SentenceTransformer(MODEL_NAME)


def iter_vault_docs():
    """Yield (relative_path, full_text) für alle Vault-MDs."""
    for md in sorted(VAULT.rglob("*.md")):
        if any(part in SKIP_DIRS for part in md.parts):
            continue
        try:
            text = md.read_text(errors="ignore").strip()
            if text:
                yield str(md.relative_to(VAULT)), text
        except Exception:
            pass


def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Teilt Text in überlappende Chunks."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + size
        chunks.append(" ".join(words[start:end]))
        start += size - overlap
    return chunks if chunks else [text[:size]]


def build_index():
    t0 = time.time()
    print("Lade Modell...")
    model = load_model()

    print("Scanne Vault...")
    docs = list(iter_vault_docs())
    print(f"  {len(docs)} Dokumente gefunden")

    all_chunks = []
    metadata = []

    for rel_path, text in docs:
        chunks = chunk_text(text)
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            metadata.append({
                "path": rel_path,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "preview": chunk[:200].replace("\n", " ")
            })

    print(f"  {len(all_chunks)} Chunks erstellt")
    print("Berechne Embeddings (kann 1-2 Minuten dauern)...")

    embeddings = model.encode(
        all_chunks,
        batch_size=64,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # Inner Product = Cosine Similarity (bei normalisierten Vektoren)
    index.add(embeddings.astype(np.float32))

    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_PATH))
    META_PATH.write_text(json.dumps(metadata, ensure_ascii=False, indent=2))

    elapsed = time.time() - t0
    print(f"\nFertig in {elapsed:.1f}s:")
    print(f"  Dokumente:  {len(docs)}")
    print(f"  Chunks:     {len(all_chunks)}")
    print(f"  Dimensionen: {dim}")
    print(f"  Index:      {INDEX_PATH}")


def search(query, top_k=6):
    """Gibt [(score, path, preview)] zurück."""
    if not INDEX_PATH.exists() or not META_PATH.exists():
        return []

    model = load_model()
    metadata = json.loads(META_PATH.read_text())
    index = faiss.read_index(str(INDEX_PATH))

    q_emb = model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True
    ).astype(np.float32)

    scores, indices = index.search(q_emb, top_k * 3)

    seen_paths = set()
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        meta = metadata[idx]
        path = meta["path"]
        if path in seen_paths:
            continue
        seen_paths.add(path)
        results.append((float(score), path, meta["preview"]))
        if len(results) >= top_k:
            break

    return results


def get_context_for_query(query, top_k=5):
    """Gibt zusammengesetzten Kontext-String für Claude zurück."""
    results = search(query, top_k=top_k)
    if not results:
        return ""

    parts = ["## RELEVANTE VAULT-EINTRÄGE (semantische Suche)\n"]
    for score, path, preview in results:
        try:
            full_text = (VAULT / path).read_text(errors="ignore")[:3000]
        except Exception:
            full_text = preview
        parts.append(f"### {path} (Relevanz: {score:.2f})\n{full_text}\n")

    return "\n".join(parts)


if __name__ == "__main__":
    if "--check" in sys.argv:
        if INDEX_PATH.exists() and META_PATH.exists():
            meta = json.loads(META_PATH.read_text())
            print(f"Index vorhanden: {len(meta)} Chunks")
        else:
            print("Kein Index gefunden. Starte: python3 _agent/rag_index.py")
    else:
        build_index()
