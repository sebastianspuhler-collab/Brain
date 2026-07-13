#!/usr/bin/env python3
"""
Prozessia Brain Web Server
Start: python3 _agent/brain_server.py
Läuft auf http://localhost:3001
"""

import json
import os
import sys
import socket
import threading
import re
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from pathlib import Path
from datetime import datetime, timedelta

VAULT = Path(__file__).parent.parent
sys.path.insert(0, str(VAULT / "_agent"))
PORT = 3001
AUTOPOSTER = VAULT / "_inbox" / "Branding" / "claude-linkedin-auto-poster"

import anthropic
ANTHROPIC = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def _response_text(response) -> str:
    """Extrahiert den Text aus einer Claude-Antwort. content[0] ist NICHT
    zuverlässig der Text-Block - bei aktiviertem Thinking steht davor ein
    ThinkingBlock ohne .text-Attribut, was content[0].text crashen lässt."""
    for block in response.content:
        if block.type == "text":
            return block.text
    return ""


# Load existing clients
try:
    import gmail_client
    GMAIL_OK = gmail_client.is_authenticated()
except Exception as e:
    GMAIL_OK = False
    print(f"Gmail: nicht verbunden ({e})")

try:
    import outlook_client
    OUTLOOK_OK = outlook_client.is_authenticated()
except Exception as e:
    OUTLOOK_OK = False
    print(f"Outlook: nicht verbunden ({e})")

# Simple in-process cache
_cache: dict = {}
CACHE_TTL_MAIL = 60    # 1 Minute für E-Mails
CACHE_TTL = 300        # 5 Minuten für alles andere

# ── RAG (FAISS) ──────────────────────────────────────────────────────────────
_rag_model = None
_rag_index = None
_rag_meta  = None

def _load_rag():
    global _rag_model, _rag_index, _rag_meta
    if _rag_index is not None:
        return True
    try:
        import faiss, numpy as np
        from sentence_transformers import SentenceTransformer
        idx_path  = VAULT / "_agent" / "vault.index"
        meta_path = VAULT / "_agent" / "vault_metadata.json"
        if not idx_path.exists() or not meta_path.exists():
            return False
        _rag_index = faiss.read_index(str(idx_path))
        raw = json.loads(meta_path.read_text())
        _rag_meta  = raw if isinstance(raw, list) else list(raw.values())
        _rag_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        return True
    except Exception:
        return False

def rag_search(query: str, k: int = 15) -> str:
    if _rag_index is None or _rag_model is None:
        return ""
    try:
        import numpy as np

        # Multi-Query: Hauptsuche + extrahierte Entitäten
        queries = [query]
        entities = re.findall(r'\b[A-ZÄÖÜ][a-zäöüß]{2,}\b', query)
        for e in entities[:4]:
            if e.lower() not in ('ich','sie','der','die','das','was','wie','bitte','hast','gibt','kann','bitte','welche','haben','sein'):
                queries.append(e)

        seen = set()
        snippets = []
        for q in queries:
            vec = _rag_model.encode([q]).astype(np.float32)
            D, I = _rag_index.search(vec, k)
            for dist, idx in zip(D[0], I[0]):
                if idx < 0 or idx >= len(_rag_meta) or idx in seen:
                    continue
                seen.add(idx)
                m = _rag_meta[idx]
                path = m.get("path", "") if isinstance(m, dict) else str(m)
                # Immer aktuellen Dateiinhalt lesen (nicht gecachten Chunk)
                try:
                    content = (VAULT / path).read_text(errors="ignore")[:1500]
                except Exception:
                    content = m.get("content", "") if isinstance(m, dict) else ""
                if not content:
                    continue
                # Relevanz-Boost: Kunden- und Email-Dateien bevorzugen
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


def get_mentioned_files(messages: list) -> str:
    """Dateipfade aus dem Gespräch (User UND Brain-Antworten) direkt einlesen.

    Erkennt:
    - Explizite Pfade mit Verzeichnis (Sales/Handelsvertreter/Datei.md)
    - Dateinamen mit Klammern und Leerzeichen (Datei (1).md)
    - Pfade die Brain Claude selbst in früheren Antworten genannt hat
    """
    # Alle Nachrichten der letzten 16 Turns — User UND Assistant
    all_text = " ".join(m.get("content", "") for m in messages[-16:])

    # Erweitertes Regex: erlaubt Klammern, Ziffern am Anfang, Leerzeichen im Namen
    PATH_RE = re.compile(
        r'(?:[A-Za-z0-9_][A-Za-z0-9_\-. ()/]*?/)?'   # optionaler Pfad
        r'[A-Za-z0-9_][A-Za-z0-9_\-. ()]*'             # Dateiname (Ziffernstart OK)
        r'\.(?:md|txt|json|html)',                       # Endung
        re.UNICODE,
    )

    results = []
    seen = set()

    for raw_p in PATH_RE.findall(all_text):
        p = raw_p.strip()
        if p in seen or len(p) < 4:
            continue
        seen.add(p)
        # 1. Exakter Pfad relativ zum Vault
        full = VAULT / p
        if full.exists() and full.is_file():
            try:
                content = full.read_text(errors="ignore")[:5000]
                results.append(f"[DIREKT GELESEN: {p}]\n{content}")
                continue
            except Exception:
                pass
        # 2. Dateiname ohne Pfad: im ganzen Vault suchen
        stem = Path(p).name
        if len(stem) > 4:
            for hit in VAULT.rglob(stem):
                if hit.is_file():
                    try:
                        content = hit.read_text(errors="ignore")[:5000]
                        results.append(f"[GEFUNDEN: {hit.relative_to(VAULT)}]\n{content}")
                        break
                    except Exception:
                        pass

    return "\n\n".join(results)


def search_vault_by_name(query: str, history: list = None) -> str:
    """Findet Vault-Dateien anhand von Schlüsselwörtern im Query und in der History.

    Löst das Problem: Brain Claude nennt einen Dateinamen, kann ihn aber nicht lesen.
    Diese Funktion sucht im Vault nach Dateien die zu den Stichwörtern passen.
    """
    # Keywords: Großgeschriebene Wörter (Namen, Firmennamen), Wörter in Anführungszeichen
    all_text = query
    if history:
        # Aus den letzten 6 Brain-Antworten: Eigennamen und Dateinamen extrahieren
        for m in history[-6:]:
            if m.get("role") == "assistant":
                all_text += " " + m.get("content", "")

    # Wörter mit ≥4 Zeichen, Großbuchstabe, keine reinen Stoppwörter
    STOPWORDS = {"Datei", "Vault", "Dokument", "Inhalt", "Hier", "Diese", "Dies",
                 "Damit", "Habe", "Kann", "Kein", "Nicht", "Sebastian", "Brain"}
    candidates = set()
    for word in re.findall(r'\b[A-ZÄÖÜ][a-zA-ZäöüÄÖÜß]{3,}\b', all_text):
        if word not in STOPWORDS:
            candidates.add(word.lower())
    # Auch explizit genannte .md-Dateinamen (ohne vollen Pfad)
    for fname in re.findall(r'\b[\w\- ()]+\.md\b', all_text):
        candidates.add(Path(fname).stem.lower()[:20])

    if not candidates:
        return ""

    results = []
    seen_paths = set()
    for f in VAULT.rglob("*.md"):
        rel_parts = f.relative_to(VAULT).parts
        if any(p.startswith(".") for p in rel_parts):
            continue
        # _agent/ überspringen — AUSSER email_cache (die sind suchbar)
        if "_agent" in rel_parts and "email_cache" not in rel_parts:
            continue
        f_lower = f.stem.lower()
        if any(kw in f_lower for kw in candidates) and str(f) not in seen_paths:
            seen_paths.add(str(f))
            try:
                content = f.read_text(errors="ignore")[:4000]
                rel = str(f.relative_to(VAULT))
                results.append(f"[VAULT-TREFFER: {rel}]\n{content}")
                if len(results) >= 4:
                    break
            except Exception:
                pass

    return "\n\n".join(results)


def get_customer_context(query: str) -> str:
    """Wenn ein Kundenname im Query vorkommt, alle seine Dateien direkt einfügen."""
    customer_dir = VAULT / "Kunden"
    if not customer_dir.exists():
        return ""
    q_lower = query.lower()
    results = []
    for cust_path in customer_dir.iterdir():
        if not cust_path.is_dir():
            continue
        name_parts = [p for p in re.split(r'[\s_\-]+', cust_path.name.lower()) if len(p) > 3]
        if not any(part in q_lower for part in name_parts):
            continue
        for f in sorted(cust_path.rglob("*.md"))[:8]:
            try:
                content = f.read_text(errors="ignore")[:2000]
                results.append(f"[{f.relative_to(VAULT)}]\n{content}")
            except Exception:
                pass
    return "\n\n".join(results)


def synthesize_context(query: str, raw_context: str) -> str:
    """Haiku analysiert Verbindungen zwischen Daten-Stücken → Kontext-Landkarte für Hauptmodell."""
    if not raw_context or len(raw_context) < 400:
        return ""
    try:
        result = ANTHROPIC.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            messages=[{"role": "user", "content": f"""Du bist ein Kontext-Analyst. Sebastians Frage: "{query[:250]}"

Analysiere die unten stehenden Daten-Fragmente und erkläre in 4-6 präzisen Bullet Points:
- Welche Mails, Dokumente und Aufgaben hängen direkt zusammen?
- Was ist die wichtigste Information zur Beantwortung der Frage?
- Welche zeitlichen oder inhaltlichen Verbindungen gibt es?
- Was fehlt möglicherweise noch?

Sei konkret und nenne Dateinamen/Absender/Daten. Kein Intro, nur Bullet Points.

DATEN:
{raw_context[:3500]}"""}]
        )
        return _response_text(result).strip()
    except Exception:
        return ""


def get_recent_conversations() -> str:
    """Lade heutige + gestrige Gesprächslogs für Kontinuität."""
    from datetime import date, timedelta
    conv_dir = VAULT / "_agent" / "conversations"
    if not conv_dir.exists():
        return ""
    today = date.today()
    parts = []
    for delta in [1, 0]:
        d = today - timedelta(days=delta)
        log_file = conv_dir / f"{d.isoformat()}.md"
        if log_file.exists():
            try:
                content = log_file.read_text(errors="ignore")
                if len(content) > 4000:
                    content = "...[frühere Einträge gekürzt]...\n" + content[-4000:]
                parts.append(f"=== GESPRÄCHSLOG {d.strftime('%d.%m.%Y')} ===\n{content}")
            except Exception:
                pass
    return "\n\n".join(parts)

threading.Thread(target=_load_rag, daemon=True).start()

# ── Inkrementelles FAISS-Update ──────────────────────────────────────────────

_faiss_lock = threading.Lock()

def _faiss_add_doc(rel_path: str, content: str):
    if _rag_index is None or _rag_model is None:
        return
    try:
        import numpy as np, faiss as _faiss
        text = content[:1500]
        vec = _rag_model.encode([text]).astype(np.float32)
        with _faiss_lock:
            _rag_index.add(vec)
            _rag_meta.append({"path": rel_path, "content": content[:1500]})
            _faiss.write_index(_rag_index, str(VAULT / "_agent" / "vault.index"))
            (VAULT / "_agent" / "vault_metadata.json").write_text(
                json.dumps(_rag_meta, ensure_ascii=False), encoding="utf-8"
            )
    except Exception:
        pass

# ── Vault Reindex (neue Dateien ohne Rebuild) ─────────────────────────────────

_SKIP_INDEX = {"_inbox", ".git", ".obsidian", "_fehler", "node_modules"}

def reindex_new_vault_files():
    """Alle .md-Dateien die noch nicht in FAISS sind sofort hinzufügen + daraus lernen."""
    if _rag_meta is None or _rag_model is None:
        return 0
    existing = {(m.get("path", "") if isinstance(m, dict) else str(m)) for m in _rag_meta}
    added = 0
    new_files = []
    for md_file in sorted(VAULT.rglob("*.md")):
        if any(skip in md_file.parts for skip in _SKIP_INDEX):
            continue
        rel = str(md_file.relative_to(VAULT))
        if rel in existing:
            continue
        try:
            content = md_file.read_text(errors="ignore")[:1500]
            if len(content) > 50:
                _faiss_add_doc(rel, content)
                new_files.append((rel, content))
                added += 1
        except Exception:
            pass
    # Aus neuen Dateien automatisch lernen (im Hintergrund)
    for rel, content in new_files:
        threading.Thread(
            target=_auto_memory_from_file,
            args=(rel, content),
            daemon=True
        ).start()
    return added


def run_inbox_and_reindex():
    """heartbeat.py ausführen, dann neue Vault-Dateien sofort in FAISS aufnehmen."""
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, str(VAULT / "_agent" / "heartbeat.py")],
        capture_output=True, text=True, cwd=str(VAULT)
    )
    added = reindex_new_vault_files()
    output = result.stdout.strip() or result.stderr.strip() or "Keine Ausgabe"
    return {"output": output, "new_indexed": added, "ok": result.returncode == 0}


def _inbox_watcher_loop():
    """Alle 30s Inbox prüfen — wenn neue Dateien da sind automatisch verarbeiten."""
    import time
    SKIP_EXT = {".js", ".ts", ".map", ".css", ".lock", ".yml", ".yaml"}
    SKIP_NAMES = {".DS_Store", "Thumbs.db"}
    while True:
        time.sleep(30)
        try:
            inbox = VAULT / "_inbox"
            neue = [f for f in inbox.rglob("*")
                    if f.is_file()
                    and f.suffix.lower() not in SKIP_EXT
                    and f.name not in SKIP_NAMES
                    and not f.name.startswith(".")
                    and "_fehler" not in str(f)
                    and "node_modules" not in str(f)
                    and "Branding" not in str(f)]
            if neue:
                print(f"  Inbox-Watcher: {len(neue)} neue Datei(en) → verarbeite...")
                run_inbox_and_reindex()
        except Exception:
            pass

threading.Thread(target=_inbox_watcher_loop, daemon=True).start()


def _hourly_inbox_loop():
    """Erzwingt einmal pro Stunde einen vollständigen Inbox-Durchlauf,
    unabhängig vom reaktiven 30s-Watcher (Sicherheitsnetz z.B. nach Neustarts
    oder falls der Watcher eine Datei verpasst hat)."""
    import time
    while True:
        time.sleep(3600)
        try:
            print("  Stündlicher Inbox-Check: verarbeite...")
            run_inbox_and_reindex()
        except Exception as ex:
            print(f"Stündlicher Inbox-Check Fehler: {ex}")

threading.Thread(target=_hourly_inbox_loop, daemon=True).start()

# ── E-Mail Indexer ────────────────────────────────────────────────────────────

EMAIL_CACHE_DIR = VAULT / "_agent" / "email_cache"
EMAIL_CACHE_DIR.mkdir(exist_ok=True)
_INDEXED_IDS_PATH = EMAIL_CACHE_DIR / "indexed_ids.json"

IMPORTANT_KEYWORDS = {"bestellung", "auftrag", "rechnung", "angebot", "lieferung",
                      "vertrag", "zahlung", "deadline", "dringend", "wichtig",
                      "invoice", "order", "contract"}
CUSTOMER_DOMAINS = {"schaufler", "mundinger", "nanosaar", "voigt-salus",
                    "voigtsalus", "prozessia"}

def _strip_html(text: str) -> str:
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    return re.sub(r'\s+', ' ', text).strip()

def _is_important_email(sender: str, subject: str, body: str) -> bool:
    """Filtert nur offensichtlichen Spam/Newsletter raus — lernt sonst von allem."""
    combined = (sender + " " + subject + " " + body[:200]).lower()
    spam = {"newsletter", "unsubscribe", "abmelden", "noreply", "no-reply",
            "donotreply", "marketing@", "info@mailchimp", "notification"}
    return not any(s in combined for s in spam)

# Gemeinsames Tool-Schema für alle Gedächtnis-Extraktionen (E-Mail/Datei/Chat).
# Ersetzt die frühere "Antworte NUR mit JSON" + Regex-Extraktion aus dem Fließtext:
# Tool Use liefert bereits geparste, schema-validierte Werte, kein re.search/json.loads nötig.
_MEMORY_ITEMS_TOOL = {
    "name": "save_memory_items",
    "description": "Speichert die aus dem Text extrahierten dauerhaft wichtigen Fakten für Sebastian Spuhler.",
    "input_schema": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "description": "Leeres Array, wenn nichts Speicherwertes gefunden wurde.",
                "items": {
                    "type": "object",
                    "properties": {
                        "kategorie": {
                            "type": "string",
                            "enum": ["KONTEXT", "PROZESS", "KORREKTUR", "KUNDE", "REGEL"],
                        },
                        "fakt": {
                            "type": "string",
                            "description": "Präzise Aussage auf Deutsch, mit Datum falls vorhanden.",
                        },
                    },
                    "required": ["kategorie", "fakt"],
                },
            },
        },
        "required": ["items"],
    },
}

def _extract_memory_items(prompt: str, model: str, max_tokens: int) -> list:
    """Ruft Claude mit erzwungenem Tool-Use auf und gibt die extrahierten Items zurück."""
    result = ANTHROPIC.messages.create(
        model=model,
        max_tokens=max_tokens,
        tools=[_MEMORY_ITEMS_TOOL],
        tool_choice={"type": "tool", "name": "save_memory_items"},
        messages=[{"role": "user", "content": prompt}],
    )
    for block in result.content:
        if block.type == "tool_use":
            return block.input.get("items", [])
    return []

def _auto_memory_from_email(sender: str, subject: str, body: str):
    try:
        prompt = f"""Analysiere diese E-Mail für Sebastian Spuhler (Prozessia GbR) und extrahiere wichtige Informationen.

SPEICHERN: Aufträge, Preise, Deadlines, Kundenwünsche, Zusagen, Absagen, Namen+Rollen, nächste Schritte, Entscheidungen
NICHT SPEICHERN: reine Bestätigungen ohne neuen Inhalt, Kalendereinladungen ohne Kontext

Von: {sender}
Betreff: {subject}
Inhalt: {body[:1000]}"""

        items = _extract_memory_items(prompt, "claude-haiku-4-5-20251001", 400)
        memory_path = VAULT / "_agent" / "memory.md"
        existing = memory_path.read_text(encoding="utf-8") if memory_path.exists() else ""
        for item in items:
            kat = item.get("kategorie", "KONTEXT").upper()
            fakt = item.get("fakt", "").strip()
            if fakt and len(fakt) > 10:
                key_words = set(fakt.lower().split()[:5])
                if not any(len(key_words & set(line.lower().split())) >= 3
                           for line in existing.split('\n') if line.strip()):
                    _append_to_memory(kat, f"[{subject[:40]}] {fakt}")
                    existing += f"\n{fakt}"
    except Exception:
        pass

_AUTO_REPLY_SENDER = "amin.douioui@prozessia.de"
_AUTO_REPLY_CC = "sebastian.spuhler@prozessia.de"
_AUTO_REPLIED_IDS_PATH = EMAIL_CACHE_DIR / "auto_replied_ids.json"

_AUTO_REPLY_TOOL = {
    "name": "decide_auto_reply",
    "description": "Entscheidet, ob eine Mail von Amin rein technische Deploy-/Server-Koordination ist, und formuliert ggf. die Antwort.",
    "input_schema": {
        "type": "object",
        "properties": {
            "ist_technische_koordination": {
                "type": "boolean",
                "description": (
                    "true wenn das THEMA der Mail Deploy-Status, Zugangsdaten, Code-Änderungen oder Server-Fragen ist — "
                    "auch wenn du die exakte Antwort nicht mit Sicherheit weißt (dann beantworte ehrlich mit dem was du weißt "
                    "und was noch fehlt/offen ist, das zählt trotzdem als true). "
                    "false NUR wenn das Thema klar etwas anderes ist: Geld/Rechnungen/Verträge, Kundenthemen, Persönliches, "
                    "oder wenn du wirklich nicht erkennen kannst worum es überhaupt geht."
                )
            },
            "antwort": {
                "type": "string",
                "description": "Fertige, kurze Antwort auf Deutsch. Ehrlich bleiben, was du weißt vs. nicht weißt. Leerer String wenn ist_technische_koordination false ist."
            }
        },
        "required": ["ist_technische_koordination", "antwort"]
    }
}


def _load_auto_replied_ids() -> set:
    if _AUTO_REPLIED_IDS_PATH.exists():
        try:
            return set(json.loads(_AUTO_REPLIED_IDS_PATH.read_text()))
        except Exception:
            return set()
    return set()


def _save_auto_replied_id(eid: str, existing: set):
    existing.add(eid)
    _AUTO_REPLIED_IDS_PATH.write_text(json.dumps(list(existing)), encoding="utf-8")


def _maybe_auto_reply_to_amin(e: dict):
    """Beantwortet Mails von Amin automatisch, aber NUR bei rein technischer
    Deploy-/Server-Koordination — sonst bleibt die Mail für Sebastian liegen.
    Immer CC an Sebastian, damit er jede Auto-Antwort mitbekommt."""
    sender = e.get("from", "")
    if _AUTO_REPLY_SENDER not in sender.lower():
        return

    eid = e.get("id", "")
    replied = _load_auto_replied_ids()
    if not eid or eid in replied:
        return

    try:
        subject = e.get("subject", "kein Betreff")
        body = _strip_html(e.get("body", "") or e.get("snippet", ""))[:3000]

        kontext = rag_search(f"{subject} {body[:500]}") or ""

        prompt = f"""Du bist Sebastians Second Brain (Prozessia GbR) und beantwortest hier automatisch eine Mail von Amin (Entwickler, deployt gerade das Prozessia-Brain-Backend auf einen VPS).

WICHTIG: Antworte NUR bei rein technischer Deploy-/Server-Koordination (Deploy-Status, Zugangsdaten, Code-Änderungen, Server-Fragen). Bei allem anderen (Geld, Verträge, Kundenthemen) oder bei Unklarheit: ist_technische_koordination = false, damit Sebastian selbst antwortet.

Von: {sender}
Betreff: {subject}
Inhalt: {body}

Bekannter Kontext zum Deploy-Stand:
{kontext[:2000] if kontext else "(kein zusätzlicher Kontext gefunden)"}"""

        result = ANTHROPIC.messages.create(
            model="claude-sonnet-5",
            max_tokens=1000,
            tools=[_AUTO_REPLY_TOOL],
            tool_choice={"type": "tool", "name": "decide_auto_reply"},
            messages=[{"role": "user", "content": prompt}],
        )
        decision = {}
        for block in result.content:
            if block.type == "tool_use":
                decision = block.input
                break

        if not decision.get("ist_technische_koordination") or not decision.get("antwort", "").strip():
            return

        gmail_client.reply_email(
            message_id=eid,
            thread_id=e.get("threadId", ""),
            to=sender,
            orig_subject=subject,
            orig_message_id=e.get("message_id", ""),
            orig_references=e.get("references", ""),
            body=decision["antwort"].strip(),
            cc=_AUTO_REPLY_CC,
        )
        _save_auto_replied_id(eid, replied)
        print(f"  Auto-Antwort an Amin gesendet: {subject[:50]}")
    except Exception as ex:
        print(f"Auto-Reply Fehler: {ex}")


def _auto_memory_from_file(rel_path: str, content: str):
    """Lernt aus neu verarbeiteten Vault-Dateien."""
    try:
        prompt = f"""Eine neue Datei wurde in den Prozessia-Vault aufgenommen. Extrahiere dauerhaft wichtige Fakten für Sebastian Spuhler.

SPEICHERN: Kundendaten, Preise, Vertragsdetails, Deadlines, Anforderungen, Entscheidungen, Projektstatus
NICHT SPEICHERN: Formatierungsinfos, allgemeine Erklärungen, offensichtliche Standardinhalte

Datei: {rel_path}
Inhalt (Auszug):
{content[:1500]}

Max 5 Items."""

        items = _extract_memory_items(prompt, "claude-haiku-4-5-20251001", 500)
        memory_path = VAULT / "_agent" / "memory.md"
        existing = memory_path.read_text(encoding="utf-8") if memory_path.exists() else ""
        filename = Path(rel_path).name
        for item in items:
            kat = item.get("kategorie", "KONTEXT").upper()
            fakt = item.get("fakt", "").strip()
            if fakt and len(fakt) > 15:
                key_words = set(fakt.lower().split()[:5])
                if not any(len(key_words & set(line.lower().split())) >= 3
                           for line in existing.split('\n') if line.strip()):
                    _append_to_memory(kat, f"[{filename}] {fakt}")
                    existing += f"\n{fakt}"
    except Exception:
        pass

_DEEP_SCAN_DONE_PATH = EMAIL_CACHE_DIR / "deep_scan_done.flag"
_DOWNLOADED_ATTS_PATH = EMAIL_CACHE_DIR / "downloaded_attachments.json"

# Typen die wir NICHT herunterladen (irrelevant oder riesig)
_SKIP_ATT_MIME = {"text/calendar", "application/ics", "text/plain"}
_SKIP_ATT_EXT  = {".ics", ".eml", ".msg"}
_MAX_ATT_BYTES = 25 * 1024 * 1024  # 25 MB

def _load_downloaded_atts() -> set:
    try:
        return set(json.loads(_DOWNLOADED_ATTS_PATH.read_text())) if _DOWNLOADED_ATTS_PATH.exists() else set()
    except Exception:
        return set()

def _save_downloaded_att(att_id: str):
    ids = _load_downloaded_atts()
    ids.add(att_id)
    _DOWNLOADED_ATTS_PATH.write_text(json.dumps(list(ids)), encoding="utf-8")

def _haiku_classify_file(filename: str, content_preview: str, sender: str, subject: str) -> str:
    """Haiku entscheidet wo eine Datei im Vault abgelegt werden soll.
    Gibt relativen Vault-Pfad zurück z.B. 'Kunden/Mueller-GmbH/filename.pdf'."""
    try:
        tree = vault_tree(max_depth=2)
        prompt = f"""Du bist ein Dokumenten-Sortierer fuer den Prozessia-Vault (Sebastian Spuhler, Unternehmensberatung KI/Automatisierung).

Vault-Ordner:
{tree}

Zu sortierende Datei:
- Dateiname: {filename}
- Absender: {sender}
- Betreff: {subject}
- Inhalt-Vorschau: {content_preview[:600]}

Wo gehoert diese Datei hin? Antworte NUR mit dem Ziel-Pfad (relativ zum Vault), ohne Erklaerung.
Beispiele: "Kunden/Nanosaar/Dokumente/{filename}" | "Sales/Angebote/{filename}" | "Finanzen/Rechnungen/{filename}" | "_inbox/{filename}"
Wenn unklar: "_inbox/{filename}"
Antworte mit genau einem Pfad:"""
        result = ANTHROPIC.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        )
        path = _response_text(result).strip().strip('"').strip("'")
        # Sicherheitsprüfung: kein path traversal, kein _agent
        if ".." in path or path.startswith("/") or "_agent" in path:
            return f"_inbox/{filename}"
        return path
    except Exception:
        return f"_inbox/{filename}"

def _auto_download_and_classify(email_id: str, sender: str, subject: str, attachments: list):
    """Lädt Anhänge herunter, lässt Haiku klassifizieren, legt sie in den richtigen Vault-Ordner."""
    if not GMAIL_OK:
        return
    downloaded_ids = _load_downloaded_atts()

    for att in attachments:
        att_id = att.get("attachmentId", "")
        if not att_id or att_id in downloaded_ids:
            continue

        filename = att.get("filename", "anhang")
        size = att.get("size", 0)
        mime = att.get("mimeType", "")

        # Filter: überspringen wenn unerwünscht
        if mime in _SKIP_ATT_MIME:
            continue
        if Path(filename).suffix.lower() in _SKIP_ATT_EXT:
            continue
        if size > _MAX_ATT_BYTES:
            print(f"  Anhang uebersprungen (zu gross {size//1024//1024}MB): {filename}")
            continue
        if not filename or filename.startswith("."):
            continue

        try:
            print(f"  Auto-Download: {filename} von {sender[:40]}...")
            data = gmail_client.download_attachment(email_id, att_id)
            if not data:
                continue

            # Inhalt-Vorschau fuer Klassifizierung
            content_preview = ""
            if Path(filename).suffix.lower() == ".pdf":
                try:
                    import pypdf, io
                    reader = pypdf.PdfReader(io.BytesIO(data))
                    content_preview = "\n".join(
                        p.extract_text() or "" for p in reader.pages[:3]
                    )[:800]
                except Exception:
                    pass
            elif Path(filename).suffix.lower() in (".txt", ".md", ".csv"):
                try:
                    content_preview = data.decode("utf-8", errors="ignore")[:800]
                except Exception:
                    pass

            # Zielordner per Haiku bestimmen
            target_rel = _haiku_classify_file(filename, content_preview, sender, subject)
            target_path = (VAULT / target_rel).resolve()

            # Sicherheitscheck
            if not str(target_path).startswith(str(VAULT.resolve())):
                target_path = VAULT / "_inbox" / filename

            target_path.parent.mkdir(parents=True, exist_ok=True)

            # Falls Datei bereits existiert: Datum-Prefix
            if target_path.exists():
                date_slug = datetime.now().strftime("%Y-%m-%d")
                target_path = target_path.parent / f"{date_slug}-{filename}"

            target_path.write_bytes(data)
            print(f"  Gespeichert: {target_path.relative_to(VAULT)}")

            # PDF-Textextraktion als .md ablegen
            if Path(filename).suffix.lower() == ".pdf" and content_preview.strip():
                md_path = target_path.with_suffix(".md")
                md_path.write_text(
                    f"# {filename}\n*Von: {sender}*\n*Betreff: {subject}*\n\n{content_preview}",
                    encoding="utf-8"
                )
                _faiss_add_doc(str(md_path.relative_to(VAULT)),
                               f"{filename}\n{sender}\n{subject}\n{content_preview[:1500]}")

            # In FAISS indexieren
            _faiss_add_doc(str(target_path.relative_to(VAULT)),
                           f"{filename}\nVon: {sender}\nBetreff: {subject}")

            # Aus memory.md lernen
            threading.Thread(
                target=_auto_memory_from_file,
                args=(str(target_path.relative_to(VAULT)), f"Anhang: {filename}\nVon: {sender}\nBetreff: {subject}\n{content_preview[:800]}"),
                daemon=True
            ).start()

            _save_downloaded_att(att_id)

        except Exception as ex:
            print(f"  Anhang-Download-Fehler ({filename}): {ex}")


def index_new_emails(deep=False):
    if not GMAIL_OK:
        return
    # Warte bis RAG geladen
    for _ in range(10):
        if _rag_index is not None:
            break
        import time; time.sleep(2)
    if _rag_index is None:
        return

    try:
        indexed = set(json.loads(_INDEXED_IDS_PATH.read_text())) if _INDEXED_IDS_PATH.exists() else set()
        # Deep-Scan: 500 Mails beim ersten Start; danach 50 für neue Mails
        limit = 500 if deep else 50
        raw_mails = gmail_client.get_emails(top=limit)
        new_count = 0

        for e in raw_mails:
            eid = e.get("id", "")
            if not eid or eid in indexed:
                continue

            sender  = e.get("from", "")
            subject = e.get("subject", "kein Betreff")
            date    = e.get("date", "")
            body    = _strip_html(e.get("body", "") or e.get("snippet", ""))[:3000]

            # Als Markdown speichern
            date_slug = re.sub(r'[^\d]', '', date[:10]) or "00000000"
            safe_sub  = re.sub(r'[^\w\s-]', '', subject)[:40].strip().replace(' ', '-')
            filename  = f"{date_slug}-{eid[:8]}-{safe_sub}.md"
            rel_path  = f"_agent/email_cache/{filename}"
            md_content = (
                f"---\ntype: email\nid: {eid}\nfrom: {sender}\n"
                f"subject: {subject}\ndate: {date}\n---\n\n"
                f"# {subject}\n\n**Von:** {sender}\n**Datum:** {date}\n\n{body}"
            )

            filepath = EMAIL_CACHE_DIR / filename
            filepath.write_text(md_content, encoding="utf-8")

            # In FAISS aufnehmen
            _faiss_add_doc(rel_path, md_content)

            # Wichtige Mails → memory.md
            if _is_important_email(sender, subject, body):
                threading.Thread(
                    target=_auto_memory_from_email,
                    args=(sender, subject, body),
                    daemon=True
                ).start()

            # Automatische Antwort bei technischer Deploy-Koordination mit Amin
            threading.Thread(
                target=_maybe_auto_reply_to_amin,
                args=(e,),
                daemon=True
            ).start()

            # Anhänge automatisch herunterladen + einsortieren (im Hintergrund)
            attachments = e.get("attachments", [])
            if attachments and _is_important_email(sender, subject, body):
                threading.Thread(
                    target=_auto_download_and_classify,
                    args=(eid, sender, subject, attachments),
                    daemon=True
                ).start()

            indexed.add(eid)
            new_count += 1

        if new_count > 0:
            _INDEXED_IDS_PATH.write_text(json.dumps(list(indexed)), encoding="utf-8")
            print(f"  Email-Index: {new_count} neue Mails indexiert")

    except Exception as ex:
        print(f"Email-Indexer Fehler: {ex}")

def _email_indexer_loop():
    import time
    time.sleep(15)  # Warte bis RAG + Clients bereit
    # Einmaliger Deep-Scan beim ersten Start (500 Mails = ~6 Monate zurück)
    if not _DEEP_SCAN_DONE_PATH.exists():
        print("  Email Deep-Scan: lese 500 Mails ein (einmalig)...")
        index_new_emails(deep=True)
        _DEEP_SCAN_DONE_PATH.write_text("done")
        print("  Email Deep-Scan abgeschlossen.")
    while True:
        index_new_emails(deep=False)
        time.sleep(300)  # alle 5 Minuten

threading.Thread(target=_email_indexer_loop, daemon=True).start()

def cache_get(key, ttl=None):
    entry = _cache.get(key)
    if entry and (datetime.now() - entry["ts"]).seconds < (ttl or CACHE_TTL):
        return entry["data"]
    return None

def cache_set(key, data):
    _cache[key] = {"ts": datetime.now(), "data": data}

# ── System Prompt ────────────────────────────────────────────────────────────

DAYS_DE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
DAYS_SHORT = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def format_calendar_week(events: list, today: datetime) -> list:
    """Formatiert Kalender-Events als Wochenansicht (Mo-So, 2 Wochen)."""
    from collections import defaultdict
    monday = today - timedelta(days=today.weekday())
    by_date = defaultdict(list)
    for e in events:
        start = e.get("start", "")
        try:
            d = datetime.fromisoformat(start[:10]).date()
            by_date[d].append(e)
        except Exception:
            pass

    lines = ["=== KALENDER — DIESE WOCHE & NÄCHSTE WOCHE ==="]
    for week_offset in range(2):
        week_start = monday + timedelta(weeks=week_offset)
        week_label = "DIESE WOCHE" if week_offset == 0 else "NÄCHSTE WOCHE"
        lines.append(f"\n  ── {week_label} ──")
        for i in range(7):
            d = (week_start + timedelta(days=i)).date()
            day_name = DAYS_DE[d.weekday()]
            date_str = d.strftime("%d.%m.%Y")
            is_today = d == today.date()
            is_past = d < today.date()
            marker = " ◄ HEUTE" if is_today else (" [vergangen]" if is_past else "")
            day_events = sorted(by_date.get(d, []), key=lambda x: x.get("start", ""))
            if not day_events:
                # Wochentage ohne Termine nur anzeigen wenn nicht vergangen (Sa/So sowieso)
                if not is_past or is_today:
                    lines.append(f"  {day_name}, {date_str}{marker}  — frei")
            else:
                lines.append(f"  {day_name}, {date_str}{marker}:")
                for e in day_events:
                    start = e.get("start", "")
                    time_s = (start[11:16] + " Uhr") if "T" in start else "ganztägig"
                    loc = f" 📍{e['location']}" if e.get("location") else ""
                    lines.append(f"    {time_s}  {e.get('title', '')}{loc}")
    return lines


def get_overdue_tasks(today: datetime) -> list:
    """Liest context.md und gibt Aufgaben zurück deren Datum bereits vergangen ist."""
    overdue = []
    try:
        ctx = (VAULT / "_agent" / "context.md").read_text()
        for line in ctx.splitlines():
            if "- [ ]" not in line:
                continue
            for m in re.finditer(r'\b(\d{1,2})\.(\d{2})\.(?:(\d{4}))?\b', line):
                day, month = int(m.group(1)), int(m.group(2))
                year = int(m.group(3)) if m.group(3) else today.year
                try:
                    task_dt = datetime(year, month, day)
                    if task_dt.date() < today.date():
                        task_text = re.sub(r'^\s*-\s*\[[ x]\]\s*', '', line).strip()
                        overdue.append(f"  ÜBERFÄLLIG seit {task_dt.strftime('%d.%m.%Y')}: {task_text[:100]}")
                except Exception:
                    pass
    except Exception:
        pass
    return overdue


def vault_tree(max_depth: int = 3) -> str:
    skip = {".git", ".obsidian", "__pycache__", ".DS_Store", "node_modules"}
    lines = ["Prozessia-Brain/"]
    def _walk(path: Path, prefix: str, depth: int):
        if depth > max_depth:
            return
        try:
            entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except PermissionError:
            return
        entries = [e for e in entries if e.name not in skip and not e.name.startswith(".")]
        for i, entry in enumerate(entries[:60]):
            connector = "└── " if i == len(entries) - 1 else "├── "
            lines.append(f"{prefix}{connector}{entry.name}{'/' if entry.is_dir() else ''}")
            if entry.is_dir():
                ext = "    " if i == len(entries) - 1 else "│   "
                _walk(entry, prefix + ext, depth + 1)
    _walk(VAULT, "", 1)
    return "\n".join(lines)

def build_system():
    now = datetime.now()
    weekdays_de = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    weekdays_short = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    today_str = f"{weekdays_de[now.weekday()]}, {now.strftime('%d.%m.%Y')}"

    # Wochentabelle Mo–So der aktuellen Woche
    monday = now - timedelta(days=now.weekday())
    week_lines = ["Wochentage aktuell:"]
    for i in range(7):
        day = monday + timedelta(days=i)
        marker = " ← HEUTE" if day.date() == now.date() else ""
        week_lines.append(f"  {weekdays_short[i]} {day.strftime('%d.%m.%Y')}{marker}")

    parts = [
        "Du bist das persönliche Second Brain von Sebastian Spuhler (Prozessia GbR, Saarbrücken).",
        "Du hast vollständigen Zugriff auf seinen Vault, alle Kundendaten, Aufgaben, E-Mails und Dokumente.",
        "",
        "SCHREIBSTIL:",
        "Schreibe wie ein kluger, direkt informierter Kollege — nicht wie ein Chatbot oder eine KI.",
        "Nutze fließenden Text. Listen nur wenn mindestens 3 vergleichbare Punkte vorhanden sind.",
        "Sei konkret: Nenne exakte Zahlen, Daten, Namen aus den Dokumenten. Nie schätzen wenn die Daten vorhanden sind.",
        "Wenn etwas fehlt, sage klar was fehlt — kein Herumreden.",
        "",
        "ANTWORTLÄNGE (strikt einhalten):",
        "Einfache Frage (Ja/Nein, kurze Auskunft) → 1-2 Sätze.",
        "Normale Anfrage (Zusammenfassung, was steht drin?) → max 5 Sätze oder 5 Bullet-Points.",
        "Nur wenn Sebastian explizit 'vollständig', 'alles', 'gib mir den ganzen Inhalt' sagt → längere Antwort erlaubt.",
        "VERBOTEN: Lange Einleitungen ('Ich habe gesucht...', 'Basierend auf meiner Analyse...', 'Gerne helfe ich dir...').",
        "VERBOTEN: Abschlussformeln ('Lass mich wissen wenn...', 'Wenn du weitere Fragen hast...', 'Ich hoffe das hilft...').",
        "VERBOTEN: Wiederholungen — was einmal gesagt ist, wird nicht nochmal zusammengefasst.",
        "",
        "FAKTEN & DATEN:",
        "Wenn du Zahlen oder Fakten aus Dokumenten nennst, zitiere die Quelle (Dateiname oder 'laut Angebot AG0024').",
        "Erfinde NIEMALS Zahlen oder schätze ('ca.') wenn du die echten Daten im Vault hast.",
        "Bei Preisen, Terminen, Vertragsinhalten: immer direkt aus dem Dokument.",
        "",
        "ZUGRIFF:",
        "Du hast ECHTZEIT-Zugriff auf Gmail, Outlook-Kalender, den gesamten Vault und alle indizierten E-Mails.",
        "Sage NIEMALS 'kein Zugriff' — alle Dateien stehen dir zur Verfügung.",
        "",
        "TOOLS:",
        "Du hast echte Tools (read_file, search_meetings, search_emails, vault_list, vault_create, vault_move, "
        "vault_rename, vault_reorganize, download_attachment, task_add, task_done, task_remove, tasks_set, "
        "push_to_buffer, generate_linkedin_ideas, generate_linkedin_posts, generate_carousel). Nutze sie proaktiv "
        "und ohne nachzufragen — sag niemals 'kein Zugriff' oder 'kann ich nicht', sondern rufe das passende Tool auf.",
        "Wenn eine Datei bereits im Kontext steht ([DIREKT GELESEN] oder [VAULT-TREFFER]), nutze diesen Inhalt direkt statt read_file erneut aufzurufen.",
        "",
        "Wenn eine E-Mail nur 'anbei das Dokument' enthält ohne Body-Text, erkläre das klar: der Anhang war eine Datei, kein Text.",
        "Wenn Sebastian ein Datum oder eine persönliche Tatsache nennt: glaube ihm sofort, kein Widerspruch.",
        "",
        "LERNEN & KORREKTUREN:",
        "Wenn Sebastian dich korrigiert, etwas berichtigt oder dir etwas beibringt: Integriere es sofort in deine Antwort und bestätige es aktiv — sag was du gelernt hast, nicht nur 'danke'.",
        "Beispiel: Sebastian sagt 'der Serverpreis ist nicht in den 220€ drin' → du antwortest inhaltlich korrekt damit UND sagst am Ende 'Verstanden und notiert: Hetzner-Serverkosten laufen separat zur 220€ Verwaltungspauschale.'",
        "",
        "PROAKTIVE INTELLIGENZ:",
        "Wenn du beim Lesen der Daten etwas siehst das Sebastian wichtig sein könnte — eine überfällige Aufgabe, eine E-Mail die noch keine Antwort hat, ein nahender Termin, eine offene Frage — erwähne es UNGEFRAGT am Ende deiner Antwort in 1-2 Sätzen.",
        "Du bist nicht nur ein Antwortgeber sondern ein aktiver Gedankenpartner. Denke mit.",
        f"Heute: {today_str}.",
        "\n".join(week_lines), "",
        "AUTOMATISCHE AUFGABEN-PRÜFUNG (bei JEDER Antwort pflichtmäßig):",
        "1. ABGELAUFENE TERMINE: Wenn der Kalender zeigt dass ein Meeting bereits stattgefunden hat (Datum vergangen),",
        "   prüfe ob es eine offene Aufgabe dafür gibt → rufe task_done dafür auf oder update sie.",
        "2. ÜBERFÄLLIGE DEADLINES: Die Sektion '=== ÜBERFÄLLIGE AUFGABEN ===' oben zeigt vorberechnete Überfälligkeiten.",
        "   Handle diese automatisch: Wenn eindeutig erledigt → task_done aufrufen, wenn noch offen → behalte + weise darauf hin.",
        "3. SEBASTIAN SAGT ETWAS IST ERLEDIGT: Wenn er sagt 'X ist passiert', 'X ist fertig', 'X weg', 'hab X gemacht'",
        "   → SOFORT task_done oder task_remove aufrufen, KEIN Nachfragen.",
        "4. NEUER TERMIN IM KALENDER: Wenn im Kalender ein Termin steht der eine offene Aufgabe erledigt (z.B. Folgetermin",
        "   vereinbart, Angebot abgeschickt) → Aufgabe automatisch mit task_done abhaken.",
        "Ziel: Die Aufgabenliste ist IMMER aktuell. Veraltete Einträge nie stehen lassen.",
        "",
    ]

    for label, path, limit in [
        ("PROZESSIA-PROFIL", VAULT / "_agent" / "prozessia.md", 5000),
        ("AKTUELLE AUFGABEN & KONTEXT", VAULT / "_agent" / "context.md", 4000),
        ("GELERNTES & GEDÄCHTNIS", VAULT / "_agent" / "memory.md", 4000),
    ]:
        try:
            text = path.read_text()[:limit]
            parts += [f"=== {label} ===", text, ""]
        except Exception:
            pass

    try:
        parts += ["=== VAULT-ORDNERSTRUKTUR ===", vault_tree(), ""]
    except Exception:
        pass

    # Letzte Gespräche (Kontinuität über Sessions)
    try:
        conv_log = get_recent_conversations()
        if conv_log:
            parts += [conv_log, ""]
    except Exception:
        pass

    # Kalender als vollständige Wochenansicht (Diese Woche + Nächste Woche)
    try:
        if OUTLOOK_OK:
            events = api_calendar()
            if events is not None:
                cal_lines = format_calendar_week(events, now)
                parts += ["\n".join(cal_lines), ""]
    except Exception:
        pass

    # Überfällige Aufgaben vorberechnen (Server-seitig, bevor Claude antwortet)
    try:
        overdue = get_overdue_tasks(now)
        if overdue:
            parts += ["=== ÜBERFÄLLIGE AUFGABEN (Datum vergangen) ==="] + overdue + [""]
    except Exception:
        pass

    # E-Mails live einlesen
    try:
        if GMAIL_OK:
            mails = api_gmail()
            if mails:
                mail_lines = ["=== GMAIL — NEUESTE 20 E-MAILS (Echtzeit) ==="]
                for m in mails[:20]:
                    unread = "●" if m.get("unread") else " "
                    snippet = m.get("snippet", "")
                    preview = f' | {snippet}' if snippet else ''
                    msg_id = m.get("id", "")
                    # Anhang-Indikator: schnell aus E-Mail-Metadaten ableiten
                    att_hint = " [hat_anhaenge: nutze DOWNLOAD_ATTACHMENT:" + msg_id + "]" if any(
                        kw in snippet.lower() for kw in ("anbei", "anhang", "attached", "attachment", "enclosed", "see attached", "datei")
                    ) else ""
                    mail_lines.append(
                        f"  {unread} [{m.get('time','')}] id:{msg_id} | {m.get('from','')} <{m.get('email','')}> — {m.get('subject','')}{preview}{att_hint}"
                    )
                parts += ["\n".join(mail_lines), ""]
    except Exception:
        pass

    # LinkedIn + Buffer: Live-Status aus Buffer API + lokale Ideen
    try:
        buf_status = api_buffer_status()
        li_ideas   = api_linkedin_ideas()
        li_dir_path = AUTOPOSTER / "brain-direction.md"

        li_section = ["=== SOCIAL MEDIA & BUFFER (Live) ==="]

        # Geplante Posts direkt aus Buffer
        if buf_status.get("geplant"):
            li_section.append("Geplante Posts in Buffer:")
            for p in buf_status["geplant"]:
                li_section.append(f"  - {p}")
        else:
            li_section.append("Buffer Queue: leer — keine Posts geplant.")

        # Zuletzt gesendet
        if buf_status.get("gesendet"):
            li_section.append("\nZuletzt gesendet:")
            for p in buf_status["gesendet"][:3]:
                li_section.append(f"  - {p}")

        # Ideen aus lokalem JSON
        if li_ideas.get("ideen"):
            li_section.append(f"\nGenerierte Ideen ({li_ideas.get('datum','?')}, {len(li_ideas['ideen'])} Stück):")
            for i in li_ideas["ideen"][:5]:
                li_section.append(f"  - [{i['kategorie']}] {i['titel']} | Hook: {i['hook']}")

        if li_dir_path.exists():
            direction_text = li_dir_path.read_text(encoding="utf-8")
            match = re.search(r"## Aktuelle Richtung\n\n(.+?)(?:\n---|\Z)", direction_text, re.DOTALL)
            if match:
                li_section.append(f"\nRichtungsvorgabe: {match.group(1).strip()}")

        li_section.append("\nNutze die Tools generate_linkedin_ideas, generate_linkedin_posts, push_to_buffer und generate_carousel proaktiv —")
        li_section.append("du musst nichts selbst ausformulieren oder speichern, die Tools erledigen alles inkl. Buffer-Push.")
        li_section.append("Sage NIEMALS 'ich kann das nicht direkt ausführen' — du KANNST es, indem du das passende Tool aufrufst.")
        li_section.append("")
        parts += ["\n".join(li_section), ""]
    except Exception:
        pass

    return "\n".join(parts)

# ── API Handlers ─────────────────────────────────────────────────────────────

def api_gmail():
    cached = cache_get("gmail", ttl=CACHE_TTL_MAIL)
    if cached:
        return cached
    if not GMAIL_OK:
        return []
    try:
        raw = gmail_client.get_emails(top=50)
        result = []
        for e in raw:
            sender = e.get("from", "")
            m = re.match(r'"?([^"<]+)"?\s*<?([^>]*)>?', sender)
            name = m.group(1).strip().strip('"') if m else sender[:40]
            addr = m.group(2).strip() if m else sender

            date_str = e.get("date", "")
            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(date_str)
                now_tz = datetime.now(dt.tzinfo)
                delta = now_tz - dt
                if delta.days == 0:
                    time_label = dt.strftime("%H:%M")
                elif delta.days == 1:
                    time_label = "Gestern"
                else:
                    time_label = dt.strftime("%d.%m.")
            except Exception:
                time_label = date_str[:10]

            # Snippet: erst Gmail-Snippet, dann body-Anfang
            snippet = e.get("snippet", "") or e.get("body", "")
            snippet = re.sub(r'\s+', ' ', snippet).strip()[:200]

            result.append({
                "id":      e.get("id", ""),
                "from":    name,
                "email":   addr,
                "subject": e.get("subject", "(kein Betreff)"),
                "snippet": snippet,
                "time":    time_label,
                "unread":  not e.get("isRead", True),
            })
        cache_set("gmail", result)
        return result
    except Exception as ex:
        print(f"Gmail Fehler: {ex}")
        return []

def api_calendar():
    cached = cache_get("calendar")
    if cached:
        return cached

    events = []

    # Outlook Kalender
    if OUTLOOK_OK:
        try:
            raw = outlook_client.get_calendar_events(days=45)
            for e in raw:
                start_obj = e.get("start", {})
                end_obj   = e.get("end",   {})
                # Ganztagsevents haben nur "date", reguläre haben "dateTime"
                start_raw = start_obj.get("dateTime", "") or start_obj.get("date", "")
                end_raw   = end_obj.get("dateTime",   "") or end_obj.get("date",   "")
                is_allday = e.get("isAllDay", False) or ("T" not in start_raw)
                try:
                    start_dt = datetime.fromisoformat(start_raw[:19])
                    end_dt   = datetime.fromisoformat(end_raw[:19]) if end_raw else start_dt
                    if start_dt < datetime.now() - timedelta(hours=1):
                        continue
                    events.append({
                        "title":    e.get("subject", ""),
                        "start":    start_dt.strftime("%Y-%m-%dT%H:%M"),
                        "end":      end_dt.strftime("%Y-%m-%dT%H:%M"),
                        "location": e.get("location", {}).get("displayName", ""),
                        "allDay":   is_allday,
                        "type":     "meeting",
                    })
                except Exception:
                    pass
        except Exception as ex:
            print(f"Outlook Kalender Fehler: {ex}")

    # Deadlines aus context.md
    try:
        ctx = (VAULT / "_agent" / "context.md").read_text()
        for line in ctx.splitlines():
            if "- [ ]" not in line and "DEADLINE" not in line.upper():
                continue
            matches = re.findall(r'\b(\d{1,2})\.(\d{1,2})\.?(?:\s*(\d{4}))?', line)
            for match in matches:
                day, month = int(match[0]), int(match[1])
                year = int(match[2]) if match[2] else 2026
                try:
                    dt = datetime(year, month, day)
                    if dt < datetime.now() - timedelta(days=1):
                        continue
                    title = re.sub(r'[-\[\] x]', '', line.split('(')[0]).strip()
                    events.append({
                        "title":  title[:55],
                        "start":  dt.strftime("%Y-%m-%dT00:00"),
                        "type":   "deadline",
                        "allDay": True,
                    })
                except Exception:
                    pass
    except Exception:
        pass

    events.sort(key=lambda e: e.get("start", ""))
    # Deduplicate by title
    seen = set()
    unique = []
    for e in events:
        key = e["title"][:30]
        if key not in seen:
            seen.add(key)
            unique.append(e)

    result = unique[:12]
    cache_set("calendar", result)
    return result

_CONTEXT_MD = VAULT / "_agent" / "context.md"

def _parse_tasks(text: str) -> list:
    tasks = []
    for line in text.splitlines():
        if "- [ ]" in line:
            t = line.replace("- [ ]", "").strip()
            m = re.search(r'(\d{1,2})\.(\d{1,2})\.', t)
            urgency = "normal"
            if m:
                try:
                    day, month = int(m.group(1)), int(m.group(2))
                    dt = datetime(datetime.now().year, month, day)
                    days_left = (dt - datetime.now()).days
                    urgency = "urgent" if days_left <= 7 else "soon" if days_left <= 21 else "normal"
                except Exception:
                    pass
            tasks.append({"text": t, "urgency": urgency})
        elif "- [x]" in line or "- [X]" in line:
            t = line.replace("- [x]", "").replace("- [X]", "").strip()
            tasks.append({"text": t, "urgency": "done", "done": True})
    return tasks

def api_tasks():
    try:
        return _parse_tasks(_CONTEXT_MD.read_text(encoding="utf-8"))
    except Exception:
        return []

def _task_add(text: str):
    """Hängt eine neue offene Aufgabe an context.md an."""
    try:
        content = _CONTEXT_MD.read_text(encoding="utf-8")
        line = f"- [ ] {text.strip()}"
        # In "Offene Aufgaben" Abschnitt einfügen wenn vorhanden
        if "## Offene Aufgaben" in content:
            lines = content.splitlines()
            insert_after = -1
            in_section = False
            for i, l in enumerate(lines):
                if l.strip() == "## Offene Aufgaben":
                    in_section = True
                elif in_section and (l.startswith("## ") or l.startswith("# ")):
                    break
                elif in_section:
                    insert_after = i
            if insert_after >= 0:
                lines.insert(insert_after + 1, line)
                _CONTEXT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
                return True
        # Fallback: am Ende anhängen
        _CONTEXT_MD.write_text(content.rstrip() + f"\n{line}\n", encoding="utf-8")
        return True
    except Exception as e:
        print(f"task_add error: {e}")
        return False

def _task_done(text: str):
    """Markiert eine Aufgabe als erledigt (- [ ] → - [x])."""
    try:
        content = _CONTEXT_MD.read_text(encoding="utf-8")
        text_lower = text.strip().lower()
        lines = content.splitlines()
        changed = False
        for i, l in enumerate(lines):
            if "- [ ]" in l and text_lower in l.lower():
                lines[i] = l.replace("- [ ]", "- [x]", 1)
                changed = True
                break
        if changed:
            _CONTEXT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return changed
    except Exception as e:
        print(f"task_done error: {e}")
        return False

def _task_remove(text: str):
    """Entfernt eine Aufgabe aus context.md."""
    try:
        content = _CONTEXT_MD.read_text(encoding="utf-8")
        text_lower = text.strip().lower()
        lines = [l for l in content.splitlines()
                 if not (("- [ ]" in l or "- [x]" in l.lower()) and text_lower in l.lower())]
        _CONTEXT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return True
    except Exception as e:
        print(f"task_remove error: {e}")
        return False

def _tasks_replace(new_tasks: list):
    """Ersetzt alle offenen Aufgaben in context.md durch new_tasks."""
    try:
        content = _CONTEXT_MD.read_text(encoding="utf-8")
        lines = content.splitlines()
        # Alle - [ ] Zeilen entfernen, - [x] behalten
        lines = [l for l in lines if "- [ ]" not in l]
        # Neue Aufgaben nach "## Offene Aufgaben" einfügen
        if "## Offene Aufgaben" in content:
            idx = next((i for i, l in enumerate(lines) if l.strip() == "## Offene Aufgaben"), -1)
            if idx >= 0:
                new_lines = [f"- [ ] {t.strip()}" for t in new_tasks if t.strip()]
                lines[idx+1:idx+1] = new_lines
        else:
            lines.append("\n## Offene Aufgaben")
            for t in new_tasks:
                lines.append(f"- [ ] {t.strip()}")
        # Update timestamp
        new_content = "\n".join(lines)
        today = datetime.now().strftime("%Y-%m-%d")
        new_content = re.sub(r'^updated: .+$', f'updated: {today}', new_content, flags=re.MULTILINE)
        _CONTEXT_MD.write_text(new_content + "\n", encoding="utf-8")
        return True
    except Exception as e:
        print(f"tasks_replace error: {e}")
        return False

# ── Vault Operationen ────────────────────────────────────────────────────────

_INBOX_DIR = VAULT / "_inbox"

def vault_create_folder(path: str) -> dict:
    """Erstellt einen neuen Ordner im Vault."""
    target = (VAULT / path).resolve()
    if not str(target).startswith(str(VAULT.resolve())):
        return {"ok": False, "error": "Pfad ausserhalb des Vault"}
    try:
        target.mkdir(parents=True, exist_ok=True)
        return {"ok": True, "path": str(target.relative_to(VAULT))}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def vault_move(src: str, dst: str) -> dict:
    """Verschiebt eine Datei oder einen Ordner im Vault."""
    import shutil
    src_path = (VAULT / src.strip()).resolve()
    dst_path = (VAULT / dst.strip()).resolve()
    if not str(src_path).startswith(str(VAULT.resolve())):
        return {"ok": False, "error": "Quellpfad ausserhalb des Vault"}
    if not str(dst_path).startswith(str(VAULT.resolve())):
        return {"ok": False, "error": "Zielpfad ausserhalb des Vault"}
    if not src_path.exists():
        return {"ok": False, "error": f"Quelle nicht gefunden: {src}"}
    try:
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_path), str(dst_path))
        rel_src = str(src_path.relative_to(VAULT)) if src_path.exists() else src
        rel_dst = str(dst_path.relative_to(VAULT))
        # Reindex nach Move
        threading.Thread(target=reindex_new_vault_files, daemon=True).start()
        return {"ok": True, "from": src, "to": rel_dst}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def vault_rename(old: str, new_name: str) -> dict:
    """Benennt eine Datei oder einen Ordner um."""
    old_path = (VAULT / old.strip()).resolve()
    if not str(old_path).startswith(str(VAULT.resolve())):
        return {"ok": False, "error": "Pfad ausserhalb des Vault"}
    if not old_path.exists():
        return {"ok": False, "error": f"Nicht gefunden: {old}"}
    new_path = old_path.parent / new_name.strip()
    try:
        old_path.rename(new_path)
        return {"ok": True, "from": old, "to": str(new_path.relative_to(VAULT))}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def vault_list(path: str = "") -> str:
    """Listet den Inhalt eines Vault-Ordners auf."""
    target = (VAULT / path).resolve() if path else VAULT.resolve()
    if not str(target).startswith(str(VAULT.resolve())):
        return "Pfad ausserhalb des Vault"
    if not target.exists():
        return f"Ordner nicht gefunden: {path}"
    skip = {".git", ".obsidian", "__pycache__", ".DS_Store", "node_modules"}
    lines = [f"Inhalt von: {path or 'Vault-Root'}"]
    try:
        entries = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        for e in entries:
            if e.name in skip or e.name.startswith("."):
                continue
            marker = "/" if e.is_dir() else f" ({e.stat().st_size} Bytes)"
            lines.append(f"  {'[OrdNer] ' if e.is_dir() else '[Datei]  '}{e.name}{'' if e.is_dir() else marker}")
    except PermissionError:
        return "Kein Zugriff"
    return "\n".join(lines)

def search_emails(query: str, max_results: int = 5) -> str:
    """Sucht in email_cache nach Mails die zum Query passen — Dateiname (Betreff) + Header (Von/Datum)."""
    keywords = [w.lower() for w in re.split(r'[\s,;/]+', query) if len(w) >= 3]
    if not keywords:
        return "Kein Suchbegriff angegeben."

    skip_names = {"indexed_ids.json", "deep_scan_done.flag", "downloaded_attachments.json"}
    results = []
    # Dateien nach Datum sortieren (neueste zuerst, Dateinamen beginnen mit DD-)
    try:
        all_files = sorted(
            [f for f in EMAIL_CACHE_DIR.glob("*.md") if f.name not in skip_names and f.is_file()],
            key=lambda f: f.stat().st_mtime, reverse=True
        )
    except Exception:
        all_files = []

    for f in all_files:
        try:
            content = f.read_text(errors="ignore")
            # Nur den Header-Bereich durchsuchen (enthält Von:/Betreff:/Datum:) + Dateiname
            searchable = f.stem.lower() + "\n" + content[:800].lower()
            if any(kw in searchable for kw in keywords):
                results.append(f"[{f.name}]\n{content[:3500]}")
                if len(results) >= max_results:
                    break
        except Exception:
            pass

    if not results:
        return (
            f"Keine E-Mails gefunden für: '{query}'.\n"
            f"Tipp: Versuche andere Schlüsselwörter (Absender-Nachname, Firmenname, Betreff-Wort)."
        )
    return "\n\n".join(results)


def search_meetings(query: str, firma: str = "", max_results: int = 5) -> str:
    """Sucht in Kunden/*/Meetings/ und Kunden/*/Dokumente/ nach Transkripten und Besprechungsprotokollen."""
    keywords = [w.lower() for w in re.split(r'[\s,;/]+', query) if len(w) >= 2]
    if not keywords:
        return "Kein Suchbegriff angegeben."

    search_dirs = []
    kunden_dir = VAULT / "Kunden"
    if kunden_dir.exists():
        for firma_dir in sorted(kunden_dir.iterdir()):
            if not firma_dir.is_dir():
                continue
            if firma and firma.lower() not in firma_dir.name.lower():
                continue
            for sub in ("Meetings", "Dokumente"):
                sub_dir = firma_dir / sub
                if sub_dir.exists():
                    search_dirs.append(sub_dir)

    results = []
    for search_dir in search_dirs:
        for f in sorted(search_dir.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                content = f.read_text(errors="ignore")
                searchable = f.stem.lower() + "\n" + content.lower()
                if any(kw in searchable for kw in keywords):
                    rel_path = f.relative_to(VAULT)
                    results.append(f"[{rel_path}]\n{content[:3500]}")
                    if len(results) >= max_results:
                        break
            except Exception:
                pass
        if len(results) >= max_results:
            break

    if not results:
        return f"Keine Meeting-Transkripte gefunden für: '{query}'" + (f" (Firma: {firma})" if firma else "") + "."
    return "\n\n".join(results)


def vault_inbox_save(filename: str, data: bytes, sender: str = "") -> dict:
    """Speichert eine Datei in _inbox/ mit Datum-Prefix."""
    date_slug = datetime.now().strftime("%Y-%m-%d")
    safe_name = re.sub(r'[^\w\-. ]', '_', filename)
    prefix = f"{date_slug}-{safe_name}"
    dest = _INBOX_DIR / prefix
    _INBOX_DIR.mkdir(exist_ok=True)
    try:
        dest.write_bytes(data)
        # PDFs als Text transkribieren
        if Path(filename).suffix.lower() == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(str(dest))
                text = "\n\n".join(p.extract_text() or "" for p in reader.pages)
                if text.strip():
                    md_path = _INBOX_DIR / (prefix.replace(".pdf", "") + "_text.md")
                    md_path.write_text(
                        f"# {filename}\n*Anhang via Gmail — {date_slug}*\n*Absender: {sender}*\n\n{text}",
                        encoding="utf-8"
                    )
                    _faiss_add_doc(
                        str(md_path.relative_to(VAULT)),
                        f"{filename}\n{sender}\n{text[:1500]}"
                    )
            except Exception:
                pass
        _faiss_add_doc(str(dest.relative_to(VAULT)), f"{filename} von {sender} am {date_slug}")
        return {"ok": True, "path": str(dest.relative_to(VAULT)), "filename": prefix}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def api_gmail_download_attachments(message_id: str) -> dict:
    """Lädt alle Anhänge einer Gmail-Nachricht herunter, speichert in _inbox/."""
    if not GMAIL_OK:
        return {"ok": False, "error": "Gmail nicht verbunden"}
    try:
        # Mail-Metadaten für Absender
        raw_mails = gmail_client.get_emails(top=50)
        sender = ""
        subject = ""
        for m in raw_mails:
            if m.get("id") == message_id:
                sender = m.get("from", "")
                subject = m.get("subject", "")
                break

        attachments = gmail_client.get_attachments(message_id)
        if not attachments:
            return {"ok": False, "error": "Keine Anhänge in dieser Mail gefunden"}

        saved = []
        for att in attachments:
            data = gmail_client.download_attachment(message_id, att["attachmentId"])
            if data:
                result = vault_inbox_save(att["filename"], data, sender)
                saved.append({
                    "filename": att["filename"],
                    "size": att["size"],
                    "saved_as": result.get("path", "?"),
                    "ok": result.get("ok", False),
                })

        # Direkt indexieren
        threading.Thread(target=reindex_new_vault_files, daemon=True).start()

        return {
            "ok": True,
            "message_id": message_id,
            "subject": subject,
            "sender": sender,
            "attachments": saved,
            "count": len(saved),
        }
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "detail": traceback.format_exc()}

def api_vault_reorganize(instructions: str) -> dict:
    """Brain Claude analysiert Vault-Struktur und schlägt Reorganisation vor / führt sie durch."""
    try:
        # Aktuelle Struktur einlesen
        current_tree = vault_tree(max_depth=4)
        # Alle Dateien auflisten
        all_files = []
        skip = {".git", ".obsidian", "__pycache__", "_agent", "node_modules"}
        for f in sorted(VAULT.rglob("*")):
            if not f.is_file():
                continue
            parts = f.relative_to(VAULT).parts
            if any(p in skip or p.startswith(".") for p in parts):
                continue
            all_files.append(str(f.relative_to(VAULT)))

        prompt = f"""Du bist ein Vault-Organisator fuer Sebastian Spuhler (Prozessia GbR).

Anweisung: {instructions}

Aktuelle Vault-Struktur:
{current_tree}

Alle Dateien ({len(all_files)} total, Auszug):
{chr(10).join(all_files[:100])}

Erstelle einen konkreten Reorganisationsplan.
Max 20 Aktionen. Nur sichere Operationen (kein Loeschen)."""

        result = ANTHROPIC.messages.create(
            model="claude-sonnet-5",
            max_tokens=3000,
            tools=[{
                "name": "create_vault_plan",
                "description": "Erstellt einen konkreten Vault-Reorganisationsplan.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "zusammenfassung": {"type": "string", "description": "Was wird gemacht und warum."},
                        "aktionen": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "typ": {"type": "string", "enum": ["move", "create_folder", "rename"]},
                                    "von": {"type": "string", "description": "Für move/rename: aktueller Pfad."},
                                    "nach": {"type": "string", "description": "Für move: Zielpfad."},
                                    "pfad": {"type": "string", "description": "Für create_folder: neuer Ordnerpfad."},
                                    "neu": {"type": "string", "description": "Für rename: neuer Dateiname."},
                                },
                                "required": ["typ"],
                            },
                        },
                    },
                    "required": ["zusammenfassung", "aktionen"],
                },
            }],
            tool_choice={"type": "tool", "name": "create_vault_plan"},
            messages=[{"role": "user", "content": prompt}]
        )
        for block in result.content:
            if block.type == "tool_use":
                return {"ok": True, "plan": block.input}
        return {"ok": False, "error": "Kein Tool-Use in Antwort"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def execute_vault_plan(plan: dict) -> dict:
    """Fuehrt einen von api_vault_reorganize erstellten Plan aus."""
    results = []
    for action in plan.get("aktionen", []):
        typ = action.get("typ")
        try:
            if typ == "move":
                r = vault_move(action["von"], action["nach"])
            elif typ == "create_folder":
                r = vault_create_folder(action["pfad"])
            elif typ == "rename":
                r = vault_rename(action["von"], action["neu"])
            else:
                r = {"ok": False, "error": f"Unbekannter Typ: {typ}"}
            results.append({"action": action, "result": r})
        except Exception as e:
            results.append({"action": action, "result": {"ok": False, "error": str(e)}})
    ok_count = sum(1 for r in results if r["result"].get("ok"))
    return {"ok": True, "executed": len(results), "success": ok_count, "results": results}


# ── Buffer API Bridge ────────────────────────────────────────────────────────

BUFFER_ENV = VAULT / "_inbox" / "Branding" / "claude-linkedin-auto-poster" / ".env"
BUFFER_API = "https://api.buffer.com/graphql"
BUFFER_ORG = "6a15c3685a233c9c16251245"
BUFFER_CHANNELS = {
    "6a25d2578f1d11f9b260c5ee": "Sebastian Spühler",
    "6a25d2578f1d11f9b260c5ef": "Prozessia GbR",
}

def _buffer_token() -> str:
    t = os.environ.get("BUFFER_API_TOKEN", "")
    if t:
        return t
    try:
        for line in BUFFER_ENV.read_text().splitlines():
            if line.startswith("BUFFER_API_TOKEN="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return ""

def _buffer_gql(query: str, variables: dict = None) -> dict:
    import urllib.request
    token = _buffer_token()
    if not token:
        return {}
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        BUFFER_API,
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read()).get("data", {})
    except Exception:
        return {}

_POSTS_Q = """
query($orgId: OrganizationId!, $status: [PostStatus!]) {
  posts(input: { organizationId: $orgId, filter: { status: $status } }) {
    edges { node { id text status dueAt sentAt channel { id } } }
  }
}"""

def api_buffer_status() -> dict:
    cached = cache_get("buffer_status")
    if cached:
        return cached
    try:
        planned = _buffer_gql(_POSTS_Q, {"orgId": BUFFER_ORG, "status": ["scheduled", "draft"]})
        sent    = _buffer_gql(_POSTS_Q, {"orgId": BUFFER_ORG, "status": ["sent"]})

        def fmt(p):
            dt = p.get("dueAt") or p.get("sentAt") or ""
            try:
                from datetime import timezone
                d = datetime.fromisoformat(dt.replace("Z", "+00:00")).astimezone()
                dt = d.strftime("%d.%m.%Y %H:%M")
            except Exception:
                dt = dt[:16]
            kanal = BUFFER_CHANNELS.get(p["channel"]["id"], "?")
            text  = p["text"].replace("\n", " ")[:80]
            return f"{dt} | {kanal} | {text}"

        planned_posts = [e["node"] for e in planned.get("posts", {}).get("edges", [])]
        planned_posts.sort(key=lambda x: x.get("dueAt") or "")
        sent_posts = [e["node"] for e in sent.get("posts", {}).get("edges", [])]
        sent_posts.sort(key=lambda x: x.get("sentAt") or "", reverse=True)

        result = {
            "geplant": [fmt(p) for p in planned_posts],
            "gesendet": [fmt(p) for p in sent_posts[:5]],
        }
        cache_set("buffer_status", result)
        return result
    except Exception as e:
        return {"error": str(e)}

CONTENT_ENGINE_URL = "http://localhost:3002"
CONTENT_ENGINE_DIR = Path.home() / "prozessia-content-engine"

def _ensure_content_engine():
    """Startet Content Engine auf Port 3002 wenn sie nicht läuft."""
    try:
        import urllib.request
        urllib.request.urlopen(f"{CONTENT_ENGINE_URL}/health", timeout=2)
        return True  # läuft bereits
    except Exception:
        pass
    try:
        node = subprocess.run(["which", "node"], capture_output=True, text=True).stdout.strip()
        if not node:
            return False
        subprocess.Popen(
            [node, "server/index.js"],
            cwd=str(CONTENT_ENGINE_DIR),
            stdout=open("/tmp/content_engine.log", "a"),
            stderr=subprocess.STDOUT,
        )
        import time; time.sleep(3)
        urllib.request.urlopen(f"{CONTENT_ENGINE_URL}/health", timeout=2)
        return True
    except Exception as e:
        print(f"Content Engine Start fehlgeschlagen: {e}")
        return False

def api_carousel_generate(hook: str, branche: str = "Alle", saeule: str = "Wissen",
                           due_at: str = None, progress_fn=None) -> dict:
    """Vollständige Karussell-Pipeline: Slides → KI-Bilder → PDF → Cloudinary → Buffer."""
    import importlib
    if not _ensure_content_engine():
        return {"ok": False, "error": "Content Engine (Port 3002) nicht erreichbar"}
    try:
        import carousel_push
        importlib.reload(carousel_push)
        return carousel_push.run(
            hook, branche, saeule,
            due_at=due_at, verbose=False, progress_fn=progress_fn,
        )
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "detail": traceback.format_exc()}

def api_buffer_push(json_path: str = None) -> dict:
    """Ruft buffer_manager.py push auf — schiebt Posts aus beitraege-JSON nach Buffer."""
    cmd = [sys.executable, str(VAULT / "_agent" / "buffer_manager.py"), "push"]
    if json_path:
        cmd.append(json_path)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(VAULT), timeout=30)
        _cache.pop("buffer_status", None)
        ok = result.returncode == 0
        output = result.stdout.strip() or result.stderr.strip()
        if ok:
            # Erinnerungsaufgabe in context.md eintragen
            try:
                ctx_path = VAULT / "_agent" / "context.md"
                reminder = "- [ ] Post ist live – jetzt 60 Minuten Kommentare beantworten!"
                content = ctx_path.read_text(encoding="utf-8") if ctx_path.exists() else ""
                if reminder not in content:
                    header = "## Offene Aufgaben"
                    if header in content:
                        content = content.replace(header, f"{header}\n{reminder}", 1)
                    else:
                        content = content.rstrip() + f"\n\n{header}\n{reminder}\n"
                    ctx_path.write_text(content, encoding="utf-8")
            except Exception:
                pass
            output += "\n\n⚡ Post ist live — jetzt 60 Minuten Kommentare beantworten!"
        return {"ok": ok, "output": output}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def _match_task_line(line: str, target: str) -> bool:
    if "- [ ]" not in line and "- [x]" not in line.lower():
        return False
    current = re.sub(r'-\s*\[[ xX]\]\s*', '', line).strip()
    return current == target

def api_task_add(text: str) -> dict:
    text = text.strip()
    if not text:
        return {"error": "kein Text"}
    try:
        ctx_path = VAULT / "_agent" / "context.md"
        content = ctx_path.read_text(encoding="utf-8") if ctx_path.exists() else ""
        header = "## Offene Aufgaben"
        entry = f"- [ ] {text}"
        if header in content:
            content = content.replace(header, f"{header}\n{entry}", 1)
        else:
            content = content.rstrip() + f"\n\n{header}\n{entry}\n"
        ctx_path.write_text(content, encoding="utf-8")
        return {"ok": True}
    except Exception as e:
        return {"error": str(e)}

def api_task_toggle(text: str, done: bool) -> dict:
    target = text.strip()
    try:
        ctx_path = VAULT / "_agent" / "context.md"
        lines = ctx_path.read_text(encoding="utf-8").splitlines()
        marker = "[x]" if done else "[ ]"
        changed = False
        for i, line in enumerate(lines):
            if _match_task_line(line, target):
                lines[i] = re.sub(r'\[[ xX]\]', marker, line, count=1)
                changed = True
                break
        ctx_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return {"ok": True, "changed": changed}
    except Exception as e:
        return {"error": str(e)}

def api_task_delete(text: str) -> dict:
    target = text.strip()
    try:
        ctx_path = VAULT / "_agent" / "context.md"
        lines = ctx_path.read_text(encoding="utf-8").splitlines()
        removed = False
        new_lines = []
        for line in lines:
            if not removed and _match_task_line(line, target):
                removed = True
                continue
            new_lines.append(line)
        ctx_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        return {"ok": True, "removed": removed}
    except Exception as e:
        return {"error": str(e)}

# ── LinkedIn Autoposter Bridge ────────────────────────────────────────────────

def _latest_autoposter_file(prefix: str):
    out = AUTOPOSTER / "output"
    if not out.exists():
        return None
    files = sorted(out.glob(f"{prefix}-*.json"), reverse=True)
    return files[0] if files else None

def api_linkedin_ideas() -> dict:
    cached = cache_get("li_ideas")
    if cached:
        return cached
    # Marketing/LinkedIn/ bevorzugen, dann AUTOPOSTER/output als Fallback
    candidates = sorted(LINKEDIN_PATH.glob("ideen-*.json"), reverse=True) if LINKEDIN_PATH.exists() else []
    path = candidates[0] if candidates else _latest_autoposter_file("ideen")
    if not path:
        return {"ideen": [], "datum": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        result = {
            "datum": data.get("generiert_am", "")[:10],
            "ideen": [
                {
                    "typ": i.get("typ", ""),
                    "titel": i.get("titel", ""),
                    "hook": i.get("hook", ""),
                    "kategorie": i.get("kategorie", ""),
                    "format": i.get("format_empfehlung", ""),
                    "cta": i.get("cta_vorschlag", ""),
                }
                for i in data.get("ideen", [])
            ],
        }
        cache_set("li_ideas", result)
        return result
    except Exception as e:
        return {"ideen": [], "datum": None, "error": str(e)}

def api_linkedin_posts() -> dict:
    cached = cache_get("li_posts")
    if cached:
        return cached
    # Erst Marketing/LinkedIn/ suchen (kanonisch), dann AUTOPOSTER/output als Fallback
    candidates = sorted(LINKEDIN_PATH.glob("beitraege-*.json"), reverse=True) if LINKEDIN_PATH.exists() else []
    if not candidates:
        out = AUTOPOSTER / "output"
        candidates = sorted(out.glob("beitraege-*.json"), reverse=True) if out.exists() else []
    if not candidates:
        return {"posts": [], "datum": None}
    path = candidates[0]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        posts = []
        for key in ["montag", "dienstag", "mittwoch", "donnerstag", "freitag"]:
            p = data.get(key)
            if not p:
                continue
            posts.append({
                "tag": key.capitalize(),
                "termin": p.get("termin", ""),
                "idee": p.get("idee", ""),
                "text_preview": p.get("text", "")[:200],
            })
        result = {"datum": path.stem.replace("beitraege-", ""), "posts": posts}
        cache_set("li_posts", result)
        return result
    except Exception as e:
        return {"posts": [], "datum": None, "error": str(e)}

def api_linkedin_direction(prompt: str) -> dict:
    if not prompt.strip():
        return {"error": "Kein Prompt"}
    direction_path = AUTOPOSTER / "brain-direction.md"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    content = f"""# Brain-Richtungsvorgabe für LinkedIn Autoposter
*Gesetzt am: {ts} von Sebastian via Brain UI*

## Aktuelle Richtung

{prompt.strip()}

---
*Diese Datei wird beim nächsten Autoposter-Run gelesen.*
"""
    try:
        direction_path.write_text(content, encoding="utf-8")
        return {"ok": True, "path": str(direction_path)}
    except Exception as e:
        return {"error": str(e)}

def _next_posting_slot(after: datetime = None) -> str:
    """Nächster erlaubter Slot: Dienstag–Donnerstag, 07:00 oder 12:00 Uhr (Berlin)."""
    now = after or datetime.now()
    candidate = (now + timedelta(hours=2)).replace(minute=0, second=0, microsecond=0)
    for _ in range(42):  # max 3 Wochen × 2 Slots/Tag
        if candidate.weekday() in (1, 2, 3):  # Di=1, Mi=2, Do=3
            for hour in (7, 12):
                slot = candidate.replace(hour=hour, minute=0)
                if slot > now + timedelta(hours=2):
                    return slot.strftime("%Y-%m-%dT%H:00:00+02:00")
        candidate = (candidate + timedelta(days=1)).replace(hour=0)
    return (now + timedelta(days=2)).strftime("%Y-%m-%dT07:00:00+02:00")


def api_linkedin_generate_ideas(focus: str = "") -> dict:
    direction_path = AUTOPOSTER / "brain-direction.md"
    current_direction = ""
    if direction_path.exists():
        match = re.search(r"## Aktuelle Richtung\n\n(.+?)(?:\n---|\Z)",
                          direction_path.read_text(encoding="utf-8"), re.DOTALL)
        if match:
            current_direction = match.group(1).strip()

    prompt = f"""Du bist LinkedIn-Content-Stratege für Prozessia.

Zielgruppe: Einkaufsleiter und Geschäftsführer in produzierenden Betrieben, 20–80 MA, DACH.
Prozessia automatisiert Beschaffungsprozesse und Stücklistenprüfung — keine Beratung, konkrete Agenten die Arbeit abnehmen.

{f"Richtungsvorgabe: {current_direction}" if current_direction else ""}
{f"Zusätzlicher Fokus: {focus}" if focus else ""}

Jede Idee bekommt EINEN dieser drei Post-Typen:
- Typ A – Schmerz-Post: Ich-Perspektive, konkreter Alltags-Schmerz der Zielgruppe, keine Lösung im ersten Satz
- Typ B – Carousel/Dokument-Post: Framework, Checkliste oder Schritt-für-Schritt (3–7 Punkte)
- Typ C – Story-Post: anonymes Vorher/Nachher eines Kunden mit konkreten Zahlen (Zeit, Geld, Aufwand)

Generiere GENAU 10 Ideen: 4× Typ A, 3× Typ B, 3× Typ C.

VERBOTEN für jeden Hook und Post:
- Statistik oder Prozentzahl als erster Satz
- Wörter: innovativ, nachhaltig, ganzheitlich, Lösungen, Transformation
- Engagement-Bait ("Teile diesen Post", "Tag jemanden")
- Compliance-Sprache

PFLICHT für jeden Hook:
- Stoppt den Scroll innerhalb von 3 Sekunden
- Ich-Perspektive ODER direkte Du-Ansprache (nicht beides)
- Kein vollständiger Satz — eher Fragment oder Frage

Generiere GENAU 10 Ideen: 4× Typ A, 3× Typ B, 3× Typ C."""

    idee_schema = {
        "type": "object",
        "properties": {
            "typ": {"type": "string", "enum": ["A", "B", "C"]},
            "titel": {"type": "string", "description": "Max 60 Zeichen."},
            "hook": {"type": "string", "description": "Erste Zeile, max 80 Zeichen, stoppt den Scroll."},
            "kern_botschaft": {"type": "string", "description": "Was der Leser mitnimmt."},
            "branche": {"type": "string", "enum": ["Werkzeugbau", "Maschinenbau", "Lohnfertiger", "Elektrotechnik", "Allgemein"]},
            "zielgruppe_spezifisch": {"type": "string", "description": "z.B. 'Einkaufsleiter, 45 MA, Werkzeugbau'."},
            "format_empfehlung": {"type": "string", "enum": ["Text", "Karussell", "Liste"]},
            "cta_vorschlag": {"type": "string", "description": "Eine spezifische Frage für Kommentare — kein Engagement-Bait."},
        },
        "required": ["typ", "titel", "hook", "kern_botschaft", "branche", "zielgruppe_spezifisch", "format_empfehlung", "cta_vorschlag"],
    }

    try:
        result = ANTHROPIC.messages.create(
            model="claude-sonnet-5",
            max_tokens=4000,
            tools=[{
                "name": "save_linkedin_ideas",
                "description": "Speichert die generierten LinkedIn-Post-Ideen.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "ideen": {"type": "array", "items": idee_schema},
                    },
                    "required": ["ideen"],
                },
            }],
            tool_choice={"type": "tool", "name": "save_linkedin_ideas"},
            messages=[{"role": "user", "content": prompt}]
        )
        data = None
        for block in result.content:
            if block.type == "tool_use":
                data = block.input
                break
        if data is None:
            return {"error": "Kein Tool-Use in Antwort"}
        data["generiert_am"] = datetime.now().isoformat()
        data["anzahl"] = len(data.get("ideen", []))

        out_path = AUTOPOSTER / "output" / f"ideen-{datetime.now().strftime('%Y-%m-%d')}.json"
        out_path.parent.mkdir(exist_ok=True)
        out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

        # Cache invalidieren damit neue Ideen sofort sichtbar sind
        _cache.pop("li_ideas", None)

        return {"ok": True, "anzahl": data["anzahl"], "ideen": [
            {"typ": i.get("typ",""), "titel": i.get("titel",""), "hook": i.get("hook",""),
             "kategorie": i.get("kategorie",""), "format": i.get("format_empfehlung",""),
             "cta": i.get("cta_vorschlag","")}
            for i in data.get("ideen", [])
        ]}
    except Exception as e:
        return {"error": str(e)}

LINKEDIN_PATH = VAULT / "Marketing" / "LinkedIn"

def api_linkedin_generate_posts(spec: str) -> dict:
    """Schreibt fertige LinkedIn Post-Texte basierend auf Spec und speichert sie."""
    direction_path = AUTOPOSTER / "brain-direction.md"
    current_direction = ""
    if direction_path.exists():
        m = re.search(r"## Aktuelle Richtung\n\n(.+?)(?:\n---|\Z)",
                      direction_path.read_text(encoding="utf-8"), re.DOTALL)
        if m:
            current_direction = m.group(1).strip()

    prompt = f"""Du bist LinkedIn-Texter für Prozessia.
Zielgruppe: Einkaufsleiter und GFs in produzierenden Betrieben, 20–80 MA, DACH.

POST-TYP-REGELN (immer einhalten):
Typ A – Schmerz-Post:
  Erste Zeile = konkreter Schmerz aus Ich-Sicht. Keine Lösung vor Zeile 5.
  Endet mit einer direkten Frage an die Leser.
Typ B – Carousel/Dokument-Post:
  Nummerierte Punkte, jeder auf eigener Zeile. Kurzes Intro, kurzes Outro.
  Endet mit Frage oder Hinweis auf weitere Ressource.
Typ C – Story-Post:
  Anonym. Beginnt mit "Ein Betrieb..." oder "Vor drei Monaten...".
  Nie echte Namen. Klares Vorher/Nachher mit konkreten Zahlen.
  Endet mit Frage: "Wie ist das bei euch?"

FORMAT-REGELN (keine Ausnahmen):
- Maximal 1.200 Zeichen
- Jeder Satz maximal 15 Wörter — längere Sätze aufteilen
- Leerzeile nach jeder 2. Zeile
- Kein Emoji außer höchstens 1 ganz am Ende
- Maximal 3 Hashtags am Ende
- KEINE Hashtags über 1 Mio Follower: #KI, #Digitalisierung, #Innovation, #Automatisierung sind verboten
- Erlaubte Hashtags: #Werkzeugbau, #Einkauf, #Beschaffung, #Mittelstand, #Prozessia, #Maschinenbau, #KIEinkauf
- Keine externen URLs im Post-Text — wenn Link nötig: "(Link in den Kommentaren)" an das Ende
- Keine Firmen- oder Personennamen — auch keine erkennbaren Details
- VERBOTENE WÖRTER: innovativ, nachhaltig, ganzheitlich, Lösungen, Transformation, in der heutigen Zeit

PFLICHT in jedem Post:
- Erste Zeile stoppt den Scroll — Fragment oder provokante These, kein Vollsatz
- Ich-Perspektive ODER direkte Du-Ansprache
- Eine einzige spezifische Frage ganz am Ende

{f"Richtungsvorgabe: {current_direction}" if current_direction else ""}

Spezifikation:
{spec}

Datum-Felder exakt wie in der Spezifikation angegeben (YYYY-MM-DD)."""

    try:
        result = ANTHROPIC.messages.create(
            model="claude-sonnet-5",
            max_tokens=6000,
            tools=[{
                "name": "save_linkedin_posts",
                "description": "Speichert die ausformulierten LinkedIn-Posts.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "posts": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "typ": {"type": "string", "enum": ["A", "B", "C"]},
                                    "tag": {"type": "string", "enum": ["Dienstag", "Mittwoch", "Donnerstag"]},
                                    "datum": {"type": "string", "description": "YYYY-MM-DD, exakt wie in der Spezifikation."},
                                    "thema": {"type": "string"},
                                    "text": {"type": "string", "description": "Vollständiger Post-Text."},
                                },
                                "required": ["typ", "tag", "datum", "thema", "text"],
                            },
                        },
                    },
                    "required": ["posts"],
                },
            }],
            tool_choice={"type": "tool", "name": "save_linkedin_posts"},
            messages=[{"role": "user", "content": prompt}]
        )
        posts = []
        for block in result.content:
            if block.type == "tool_use":
                posts = block.input.get("posts", [])
                break

        if not posts:
            return {"error": "Keine Posts extrahiert"}

        # Speichern in Marketing/LinkedIn/ (kanonischer Pfad, von buffer_manager.py gelesen)
        out_data = {
            "generiert_am": datetime.now().isoformat(),
            "kanaele": list(BUFFER_CHANNELS.keys()),  # beide Kanäle
            "planungen": [],
        }
        # Slots sequenziell vergeben: jeder Post bekommt den nächsten freien Di/Mi/Do-Slot
        slot_cursor = datetime.now()
        for p in posts:
            key = p.get("tag", "").lower()
            # Datum aus Spec bevorzugen, sonst nächsten freien Slot berechnen
            raw_datum = p.get("datum", "")
            if raw_datum and re.match(r"\d{4}-\d{2}-\d{2}", raw_datum):
                # Prüfen ob Datum ein erlaubter Wochentag ist (Di-Do)
                try:
                    slot_dt = datetime.strptime(raw_datum, "%Y-%m-%d")
                    if slot_dt.weekday() in (1, 2, 3):  # Di/Mi/Do
                        termin = f"{raw_datum}T07:00:00+02:00"
                    else:
                        termin = _next_posting_slot(slot_cursor)
                        slot_cursor = datetime.fromisoformat(termin[:19]) + timedelta(days=1)
                except Exception:
                    termin = _next_posting_slot(slot_cursor)
                    slot_cursor = datetime.fromisoformat(termin[:19]) + timedelta(days=1)
            else:
                termin = _next_posting_slot(slot_cursor)
                slot_cursor = datetime.fromisoformat(termin[:19]) + timedelta(days=1)
            out_data[key] = {
                "termin": termin,
                "idee": p.get("thema", ""),
                "text": p.get("text", ""),
                "typ": p.get("typ", ""),
            }
        LINKEDIN_PATH.mkdir(parents=True, exist_ok=True)
        out_path = LINKEDIN_PATH / f"beitraege-{datetime.now().strftime('%Y-%m-%d')}.json"
        out_path.write_text(json.dumps(out_data, ensure_ascii=False, indent=2), encoding="utf-8")
        _cache.pop("li_posts", None)
        return {"ok": True, "posts": posts, "path": str(out_path)}
    except Exception as e:
        return {"error": str(e)}

def api_linkedin_direction_get() -> dict:
    direction_path = AUTOPOSTER / "brain-direction.md"
    if not direction_path.exists():
        return {"prompt": ""}
    try:
        text = direction_path.read_text(encoding="utf-8")
        # Extract content between "## Aktuelle Richtung" and "---"
        match = re.search(r"## Aktuelle Richtung\n\n(.+?)(?:\n---|\Z)", text, re.DOTALL)
        return {"prompt": match.group(1).strip() if match else text.strip()}
    except Exception:
        return {"prompt": ""}

# ── Conversation Logging & Memory ────────────────────────────────────────────

CONV_DIR = VAULT / "_agent" / "conversations"
CONV_DIR.mkdir(exist_ok=True)

def log_turn(role: str, content: str):
    today = datetime.now().strftime("%Y-%m-%d")
    path = CONV_DIR / f"{today}.md"
    if not path.exists():
        path.write_text(f"---\ndate: {today}\ntitle: Gespräch {today}\n---\n\n", encoding="utf-8")
    label = "**Sebastian:**" if role == "user" else "**Brain:**"
    ts = datetime.now().strftime("%H:%M")
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n### {ts}\n{label}\n{content.strip()}\n")

def _append_to_memory(kategorie: str, fakt: str):
    memory_path = VAULT / "_agent" / "memory.md"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n- [{ts}] {fakt.strip()}"
    content = memory_path.read_text(encoding="utf-8") if memory_path.exists() else ""
    header = f"## {kategorie}"
    if header in content:
        content = content.replace(header, f"{header}{entry}", 1)
    else:
        content = content.rstrip() + f"\n\n{header}{entry}\n"
    memory_path.write_text(content, encoding="utf-8")

_CORRECTION_SIGNALS = {"nein", "falsch", "stimmt nicht", "das ist nicht", "eigentlich",
                       "merke dir", "vergiss nicht", "das weißt du doch", "du liegst falsch",
                       "nicht korrekt", "falsche zahl", "der preis ist", "kostet", "nicht in",
                       "kein zugriff", "das liegt bei dir", "du hast doch", "ist doch"}

def auto_remember(user_msg: str, assistant_msg: str):
    """Sonnet extrahiert Fakten — mit Deduplizierung und Korrektur-Priorität."""
    try:
        is_correction = any(sig in user_msg.lower() for sig in _CORRECTION_SIGNALS)
        prompt = f"""Du bist der Memory-Manager des Prozessia Brain.
Analysiere diesen Gesprächsaustausch und extrahiere NUR dauerhaft wichtige Informationen für Sebastian Spuhler.

{"⚠️ ACHTUNG: Sebastian korrigiert etwas — diese Korrektur unbedingt als KORREKTUR-Eintrag speichern!" if is_correction else ""}

SPEICHERN — aggressiv, lieber zu viel als zu wenig:
- Korrekturen (Sebastian sagt etwas ist falsch/anders) → KORREKTUR
- Neue Fakten: Preise, Vertragsinhalte, Deadlines, Entscheidungen → KONTEXT
- Kundensituationen, Projektstände, neue Kontakte → KUNDE
- Arbeitsregeln und Präferenzen von Sebastian → REGEL
- Prozessentscheidungen, Abläufe → PROZESS
- Alles was Sebastian explizit erwähnt und relevant klingt → KONTEXT

NICHT SPEICHERN:
- Reine Informationsabfragen ohne neuen Fakt
- Bereits bekannte Dinge (kein Duplikat)

Sebastian: {user_msg[:800]}

Brain: {assistant_msg[:400]}

Max 3 Items."""

        items = _extract_memory_items(prompt, "claude-sonnet-5", 300)
        saved = []
        for item in items:
            kat = item.get("kategorie", "KONTEXT").upper()
            fakt = item.get("fakt", "").strip()
            if fakt and len(fakt) > 15:
                # Deduplizierung: nicht speichern wenn sehr ähnlicher Eintrag existiert
                memory_path = VAULT / "_agent" / "memory.md"
                existing = memory_path.read_text(encoding="utf-8") if memory_path.exists() else ""
                key_words = set(fakt.lower().split()[:5])
                if not any(len(key_words & set(line.lower().split())) >= 3
                           for line in existing.split('\n') if line.strip()):
                    _append_to_memory(kat, fakt)
                    saved.append(fakt)
        return saved
    except Exception:
        return []

def api_remember(text: str) -> dict:
    if not text.strip():
        return {"error": "kein Text"}
    try:
        _append_to_memory("KONTEXT", text)
        return {"ok": True}
    except Exception as e:
        return {"error": str(e)}

# ── Tool Use API: Tool-Definitionen ──────────────────────────────────────────
# Ersetzt das alte [SIGNAL: ...]-Textparsing durch die echte Anthropic Tool Use API:
# Claude ruft diese Tools strukturiert auf (tool_use-Blöcke), der Server führt sie aus
# und schickt das Ergebnis als tool_result zurück, bevor Claude seine finale Antwort schreibt.

TOOLS = [
    {
        "name": "read_file",
        "description": (
            "Liest eine Datei aus dem Vault (Verträge, Angebote, Kundendokumente etc.). "
            "Nutze dies wenn eine Datei erwähnt wird, die noch nicht im Kontext steht — "
            "nie 'kann ich nicht einsehen' sagen, sondern dieses Tool nutzen. "
            "Akzeptiert exakten Pfad, reinen Dateinamen oder ein Stichwort im Dateinamen; "
            "der Server sucht automatisch im ganzen Vault danach. PDF/DOCX werden automatisch als Text extrahiert."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Pfad, Dateiname oder Stichwort, z.B. 'Sales/Geginat/Vertriebsvereinbarung.md' oder 'Geginat'"}
            },
            "required": ["path"],
        },
    },
    {
        "name": "search_meetings",
        "description": (
            "Durchsucht Kunden/*/Meetings/ und Kunden/*/Dokumente/ nach Transkripten und Protokollen. "
            "Immer nutzen wenn von Meetings, Besprechungen, Transkripten, Protokollen oder Calls die Rede ist."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Stichwort, z.B. 'winform' oder 'Jochen'"},
                "firma": {"type": "string", "description": "Optional: Firmenname, um die Suche auf Kunden/<Firma>/ einzugrenzen"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_emails",
        "description": (
            "Sucht NUR im E-Mail-Cache (Gmail/Outlook) nach Absender/Betreff/Inhalt. "
            "Nur nutzen wenn explizit von einer E-Mail die Rede ist (nicht von Meetings oder Dokumenten). "
            "NIEMALS vault_list auf _agent/email_cache benutzen — das listet 250+ Dateien ohne Filter, dafür immer dieses Tool."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Stichwörter mit Leerzeichen getrennt, z.B. 'Mittelstand Digital Michelle'"}
            },
            "required": ["query"],
        },
    },
    {
        "name": "vault_list",
        "description": "Zeigt den Ordnerinhalt eines Vault-Pfads — nur für Struktur-Übersichten, NICHT für E-Mail-Suche (dafür search_emails nutzen).",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Ordnerpfad relativ zum Vault-Root, leer = Root"}
            },
        },
    },
    {
        "name": "vault_create",
        "description": "Erstellt einen neuen Ordner im Vault (auch verschachtelt).",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "z.B. 'Kunden/Mueller-GmbH'"}},
            "required": ["path"],
        },
    },
    {
        "name": "vault_move",
        "description": "Verschiebt eine Datei oder einen Ordner im Vault.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "destination": {"type": "string"},
            },
            "required": ["source", "destination"],
        },
    },
    {
        "name": "vault_rename",
        "description": "Benennt eine Datei oder einen Ordner im Vault um.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "aktueller Pfad"},
                "new_name": {"type": "string", "description": "neuer Name"},
            },
            "required": ["path", "new_name"],
        },
    },
    {
        "name": "vault_reorganize",
        "description": (
            "Analysiert die Vault-Struktur mit KI, erstellt einen Reorganisationsplan (move/create_folder/rename) "
            "und führt ihn aus. Für größere Umstrukturierungen, z.B. 'Reorganisiere meine Inbox'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "instructions": {"type": "string", "description": "Anweisung in natürlicher Sprache"}
            },
            "required": ["instructions"],
        },
    },
    {
        "name": "download_attachment",
        "description": (
            "Lädt alle Anhänge einer Gmail-Mail herunter, speichert sie in _inbox/ und indexiert sie sofort. "
            "Die message_id steht im Gmail-Kontext (id-Feld). Niemals 'kann ich nicht' sagen — dieses Tool nutzen."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"message_id": {"type": "string"}},
            "required": ["message_id"],
        },
    },
    {
        "name": "task_add",
        "description": "Fügt eine neue offene Aufgabe in der Sidebar hinzu (context.md). Sidebar aktualisiert sich sofort.",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "task_done",
        "description": "Markiert eine Aufgabe (per Text oder Teiltext) als erledigt. Immer sofort nutzen wenn Sebastian sagt etwas sei erledigt/passiert/fertig — nicht nachfragen.",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "task_remove",
        "description": "Entfernt eine Aufgabe (per Text oder Teiltext) komplett aus der Liste.",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "tasks_set",
        "description": "Ersetzt die gesamte offene Aufgabenliste durch eine neue Liste.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tasks": {"type": "array", "items": {"type": "string"}, "description": "Liste der neuen offenen Aufgaben"}
            },
            "required": ["tasks"],
        },
    },
    {
        "name": "push_to_buffer",
        "description": "Pusht die neueste generierte beitraege-*.json (LinkedIn-Posts) sofort nach Buffer, für beide Kanäle (Sebastian + Prozessia).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "generate_linkedin_ideas",
        "description": "Generiert 10 neue LinkedIn-Ideen (4x Typ A Schmerz-Post, 3x Typ B Karussell, 3x Typ C Story) via Claude und speichert sie.",
        "input_schema": {
            "type": "object",
            "properties": {"focus": {"type": "string", "description": "Optionaler thematischer Fokus"}},
        },
    },
    {
        "name": "generate_linkedin_posts",
        "description": (
            "Schreibt fertige LinkedIn-Post-Texte aus und pusht sie direkt nach Buffer (beide Kanäle). "
            "Spec-Format: 'Thema1/Datum1, Thema2/Datum2, Zielgruppe' — Datum ist optional (YYYY-MM-DD)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"spec": {"type": "string"}},
            "required": ["spec"],
        },
    },
    {
        "name": "generate_carousel",
        "description": (
            "Vollständige Karussell-Pipeline: Slides (Claude) → KI-Bilder (gpt-image-1) → PDF → Cloudinary → Buffer Document-Post. "
            "Datum optional, ohne Datum wird der nächste Di oder Fr 09:30 genommen."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "hook": {"type": "string", "description": "Hook-Text für die erste Slide"},
                "branche": {"type": "string", "description": "z.B. Werkzeugbau, Maschinenbau — Default 'Alle'"},
                "saeule": {"type": "string", "description": "Themen-Säule, Default 'Wissen'"},
                "due_date": {"type": "string", "description": "Optional YYYY-MM-DD"},
            },
            "required": ["hook"],
        },
    },
]


def _read_vault_file_content(path: Path) -> str:
    """Liest Datei — PDF, DOCX werden extrahiert, sonst Text."""
    suf = path.suffix.lower()
    if suf == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(str(path))
            text = "\n\n".join(p.extract_text() or "" for p in reader.pages)
            return text[:8000] if text.strip() else "[PDF ohne extrahierbaren Text]"
        except ImportError:
            return "[PDF — pypdf nicht installiert]"
        except Exception as e:
            return f"[PDF-Fehler: {e}]"
    if suf == ".docx":
        try:
            from docx import Document
            doc = Document(str(path))
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            return text[:8000] if text.strip() else "[DOCX ohne extrahierbaren Text]"
        except Exception as e:
            return f"[DOCX-Fehler: {e}]"
    if suf in (".png", ".jpg", ".jpeg", ".gif", ".mp4", ".zip"):
        return f"[Binärdatei — kein Textinhalt: {suf}]"
    return path.read_text(errors="ignore")[:6000]


def tool_read_file(req_path: str) -> str:
    """Liest exakten Pfad, sonst Dateiname-Suche, sonst Stichwort-Suche im ganzen Vault."""
    target = VAULT / req_path
    if target.exists() and target.is_file():
        return f"Datei: {req_path}\n\n{_read_vault_file_content(target)}"
    fname = Path(req_path).name
    for hit in VAULT.rglob(fname):
        if hit.is_file():
            rel = str(hit.relative_to(VAULT))
            return f"Datei: {rel}\n\n{_read_vault_file_content(hit)}"
    kw = req_path.lower().strip()
    for ext in ("*.md", "*.txt", "*.pdf", "*.docx"):
        for hit in VAULT.rglob(ext):
            if kw in hit.stem.lower():
                rel = str(hit.relative_to(VAULT))
                return f"Datei: {rel}\n\n{_read_vault_file_content(hit)}"
    return f"Datei nicht gefunden: {req_path}"


_TASK_TOOL_NAMES = {"task_add", "task_done", "task_remove", "tasks_set"}


def execute_tool(name: str, tool_input: dict, send_chunk=None) -> tuple:
    """Führt ein Tool aus. Gibt (text, is_error) zurück, sodass der Aufrufer den
    tool_result-Block korrekt mit is_error markieren kann statt Fehler nur im Text zu verstecken."""
    try:
        if name == "read_file":
            text = tool_read_file(tool_input.get("path", ""))
            return text, text.startswith("Datei nicht gefunden")

        if name == "search_meetings":
            query = tool_input.get("query", "")
            firma = tool_input.get("firma", "") or ""
            return search_meetings(query, firma=firma), False

        if name == "search_emails":
            return search_emails(tool_input.get("query", "")), False

        if name == "vault_list":
            path = tool_input.get("path", "") or ""
            if "email_cache" in path.lower():
                return "VAULT_LIST auf email_cache ist deaktiviert (250+ Dateien). Nutze stattdessen search_emails.", True
            return vault_list(path), False

        if name == "vault_create":
            result = vault_create_folder(tool_input.get("path", ""))
            return json.dumps(result, ensure_ascii=False), not result.get("ok")

        if name == "vault_move":
            result = vault_move(tool_input.get("source", ""), tool_input.get("destination", ""))
            return json.dumps(result, ensure_ascii=False), not result.get("ok")

        if name == "vault_rename":
            result = vault_rename(tool_input.get("path", ""), tool_input.get("new_name", ""))
            return json.dumps(result, ensure_ascii=False), not result.get("ok")

        if name == "vault_reorganize":
            instructions = tool_input.get("instructions", "")
            if send_chunk:
                send_chunk("\n\n---\n*Vault-Reorganisation: Analysiere Struktur...*")
            plan_result = api_vault_reorganize(instructions)
            if not plan_result.get("ok"):
                return f"Fehler: {plan_result.get('error','?')}", True
            plan = plan_result["plan"]
            if send_chunk:
                summary = plan.get("zusammenfassung", "")
                actions = plan.get("aktionen", [])
                send_chunk(f"\n\n**Reorganisationsplan ({len(actions)} Aktionen):**\n{summary}")
                send_chunk("\n\n*Fuehre aus...*")
            exec_result = execute_vault_plan(plan)
            return (
                f"Reorganisation abgeschlossen: {exec_result['success']}/{exec_result['executed']} "
                f"Aktionen erfolgreich.",
                False,
            )

        if name == "download_attachment":
            msg_id = tool_input.get("message_id", "")
            if send_chunk:
                send_chunk(f"\n\n---\n*Lade Anhänge fuer Mail {msg_id[:12]}... herunter...*")
            result = api_gmail_download_attachments(msg_id)
            if not result.get("ok"):
                return f"Fehler: {result.get('error','?')}", True
            files_info = "\n".join(
                f"  - {a['filename']} ({a['size']} Bytes) → {a['saved_as']}"
                for a in result.get("attachments", [])
            )
            return (
                f"{result['count']} Anhang/Anhaenge heruntergeladen aus: {result.get('subject','?')}\n"
                f"{files_info}\n\nDateien liegen in _inbox/ und sind indexiert.",
                False,
            )

        if name == "task_add":
            ok = _task_add(tool_input.get("text", ""))
            return ("Aufgabe hinzugefuegt." if ok else "Fehler beim Hinzufuegen."), not ok

        if name == "task_done":
            ok = _task_done(tool_input.get("text", ""))
            return ("Aufgabe als erledigt markiert." if ok else "Aufgabe nicht gefunden."), not ok

        if name == "task_remove":
            ok = _task_remove(tool_input.get("text", ""))
            return ("Aufgabe entfernt." if ok else "Fehler beim Entfernen."), not ok

        if name == "tasks_set":
            tasks = tool_input.get("tasks", [])
            ok = _tasks_replace(tasks)
            return (f"Aufgabenliste aktualisiert: {len(tasks)} offene Aufgaben." if ok else "Fehler beim Aktualisieren."), not ok

        if name == "push_to_buffer":
            result = api_buffer_push()
            ok = result.get("ok")
            return ("Posts in Buffer eingeplant." if ok else f"Buffer-Fehler: {result.get('error','?')}"), not ok

        if name == "generate_linkedin_ideas":
            result = api_linkedin_generate_ideas(tool_input.get("focus", "") or "")
            ok = result.get("ok")
            n = result.get("anzahl", 0)
            return (f"{n} neue Ideen generiert und gespeichert." if ok else f"Fehler: {result.get('error','?')}"), not ok

        if name == "generate_linkedin_posts":
            spec = tool_input.get("spec", "")
            result = api_linkedin_generate_posts(spec)
            if not result.get("ok"):
                return f"Generierung fehlgeschlagen: {result.get('error','?')}", True
            push = api_buffer_push(result.get("path"))
            if push.get("ok"):
                return f"{len(result.get('posts',[]))} Posts generiert und in Buffer eingeplant.", False
            # Posts wurden erfolgreich generiert und gespeichert, nur der Buffer-Push schlug fehl
            return f"Posts generiert — Buffer Push: {push.get('output','?')[:200]}", False

        if name == "generate_carousel":
            hook = tool_input.get("hook", "")
            branche = tool_input.get("branche") or "Alle"
            saeule = tool_input.get("saeule") or "Wissen"
            due_date = tool_input.get("due_date")
            due_at = f"{due_date}T09:30:00+02:00" if due_date and re.match(r"\d{4}-\d{2}-\d{2}", due_date) else None
            if send_chunk:
                send_chunk(f"\n\n---\n*Karussell: Starte Pipeline fuer \"{hook}\"...*")

            def _progress(msg):
                if send_chunk:
                    send_chunk(f"\n*{msg}*")

            result = api_carousel_generate(hook, branche, saeule, due_at=due_at, progress_fn=_progress)
            if result.get("ok"):
                n = result.get("slides", 0)
                due = (result.get("due_at") or "")[:10]
                pushed = result.get("anzahl_gepusht", 0)
                titles = " | ".join((result.get("slide_titles") or [])[:3])
                return f"Karussell fertig — {n} Slides | Buffer: {pushed}x eingeplant fuer {due} | {titles}", False
            return f"Karussell-Fehler: {result.get('error','?')}", True

        return f"Unbekanntes Tool: {name}", True
    except Exception as e:
        return f"Tool-Fehler ({name}): {e}", True


# ── Auth ─────────────────────────────────────────────────────────────────────
# Passwörter für Remote-Zugriff (lokal wird automatisch durchgelassen)
_AUTH_TOKENS = {
    "prozessia2026",   # Sebastian
    "amin2026",        # Amin
}

def _check_auth(handler) -> bool:
    """Lokal immer erlaubt. Remote: Token im Header oder URL-Parameter prüfen."""
    host = handler.headers.get("Host", "")
    # Lokaler Zugriff immer erlaubt
    if "localhost" in host or "127.0.0.1" in host:
        return True
    # Token aus Header: Authorization: Bearer <token>
    auth_header = handler.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip() in _AUTH_TOKENS
    # Token aus Cookie: brain_token=<token>
    cookie = handler.headers.get("Cookie", "")
    for part in cookie.split(";"):
        if "brain_token=" in part:
            token = part.split("brain_token=", 1)[1].strip()
            if token in _AUTH_TOKENS:
                return True
    # Token aus Query-String: /?token=<token>
    from urllib.parse import urlparse, parse_qs
    qs = parse_qs(urlparse(handler.path).query)
    if qs.get("token", [""])[0] in _AUTH_TOKENS:
        return True
    return False

_LOGIN_HTML = """<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">
<title>Prozessia Brain — Login</title>
<style>*{box-sizing:border-box}body{margin:0;background:#111;display:flex;align-items:center;
justify-content:center;height:100vh;font-family:system-ui,sans-serif;color:#e0e0e0}
.card{background:#1a1a1a;border:1px solid #333;border-radius:12px;padding:40px;width:320px;text-align:center}
h2{margin:0 0 8px;font-size:18px}p{margin:0 0 24px;font-size:13px;color:#888}
input{width:100%;padding:10px 14px;background:#242424;border:1px solid #444;border-radius:8px;
color:#e0e0e0;font-size:14px;outline:none;margin-bottom:12px}
input:focus{border-color:#7c6af7}
button{width:100%;padding:10px;background:#7c6af7;border:none;border-radius:8px;color:#fff;
font-size:14px;cursor:pointer;font-weight:600}
button:hover{background:#9b8dff}.err{color:#ff6b6b;font-size:12px;margin-top:8px;display:none}
</style></head><body><div class="card">
<h2>Prozessia Brain</h2><p>Zugangscode eingeben</p>
<input type="password" id="pw" placeholder="Passwort" onkeydown="if(event.key==='Enter')login()">
<button onclick="login()">Einloggen</button>
<div class="err" id="err">Falsches Passwort</div></div>
<script>
function login(){
  const pw=document.getElementById('pw').value;
  fetch('/api/auth',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({token:pw})}).then(r=>r.json()).then(d=>{
    if(d.ok){document.cookie='brain_token='+pw+';path=/;max-age=2592000';location.reload()}
    else{document.getElementById('err').style.display='block'}
  })
}</script></body></html>"""

# ── HTTP Handler ─────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass  # quiet

    def cors_headers(self, code=200, ct="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ct)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def json_response(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.cors_headers(code)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _serve_login(self):
        body = _LOGIN_HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_html(self):
        """Liefert die Brain UI HTML-Datei aus — damit Amin nur eine URL braucht."""
        html_path = VAULT / "prozessia_brain_ui.html"
        try:
            html = html_path.read_bytes()
            # API-URL auf relativen Pfad anpassen (funktioniert lokal UND remote über Tunnel)
            html = html.replace(
                b"const API = 'http://localhost:3001'",
                b"const API = window.location.origin"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(html)
        except Exception as ex:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(ex).encode())

    def do_GET(self):
        if self.path in ("/", "/ui", "/brain"):
            if not _check_auth(self):
                self._serve_login()
                return
            self._serve_html()
            return
        # /api/status ist öffentlich (zeigt keine sensiblen Daten)
        elif self.path == "/api/status":
            ngrok_url = ""
            try:
                import urllib.request
                with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=1) as r:
                    tunnels = json.loads(r.read())["tunnels"]
                    if tunnels:
                        ngrok_url = tunnels[0]["public_url"]
            except Exception:
                pass
            self.json_response({
                "ok": True,
                "gmail": GMAIL_OK,
                "outlook": OUTLOOK_OK,
                "date": datetime.now().strftime("%d.%m.%Y"),
                "rag_docs": len(_rag_meta) if _rag_meta else 0,
                "ngrok_url": ngrok_url,
            })
            return
        # Widget-Daten: Auth via Cookie ODER wenn Seite bereits geladen (Referer check)
        # Kalender, Gmail, Tasks zeigen nur Zusammenfassungen — kein volles Auth nötig
        if self.path == "/api/gmail":
            self.json_response(api_gmail())
            return
        elif self.path == "/api/calendar":
            self.json_response(api_calendar())
            return
        elif self.path == "/api/tasks":
            self.json_response(api_tasks())
            return
        elif self.path == "/api/tasks/mtime":
            try:
                mtime = int(_CONTEXT_MD.stat().st_mtime * 1000)
            except Exception:
                mtime = 0
            self.json_response({"mtime": mtime})
            return
        # Alle anderen GET-Endpoints brauchen Auth
        if not _check_auth(self):
            self.json_response({"error": "unauthorized"}, 401)
            return
        elif self.path == "/api/linkedin/ideas":
            self.json_response(api_linkedin_ideas())
        elif self.path == "/api/linkedin/posts":
            self.json_response(api_linkedin_posts())
        elif self.path == "/api/linkedin/direction":
            self.json_response(api_linkedin_direction_get())
        elif self.path == "/api/buffer/status":
            _cache.pop("buffer_status", None)
            self.json_response(api_buffer_status())
        elif self.path.startswith("/api/gmail/attachments/"):
            msg_id = self.path.split("/api/gmail/attachments/", 1)[1].strip("/")
            if msg_id:
                self.json_response({"attachments": gmail_client.get_attachments(msg_id)} if GMAIL_OK else {"error": "Gmail nicht verbunden"})
            else:
                self.json_response({"error": "Keine message_id"}, 400)
        elif self.path.startswith("/api/vault/list"):
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(self.path).query)
            path = qs.get("path", [""])[0]
            self.json_response({"listing": vault_list(path)})
        elif self.path.startswith("/files/"):
            self._serve_file()
        elif self.path == "/api/files":
            self._list_files()
        else:
            self.json_response({"error": "not found"}, 404)

    def _serve_file(self):
        """Datei aus dem Vault zum Download ausliefern."""
        import mimetypes, urllib.parse
        rel = urllib.parse.unquote(self.path[len("/files/"):])
        # Sicherheit: kein path traversal
        target = (VAULT / rel).resolve()
        if not str(target).startswith(str(VAULT.resolve())):
            self.json_response({"error": "forbidden"}, 403)
            return
        if not target.exists() or not target.is_file():
            self.json_response({"error": "not found"}, 404)
            return
        mime = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", f'attachment; filename="{target.name}"')
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _list_files(self):
        """Alle Dateien im Vault auflisten (für Datei-Browser)."""
        _SKIP = {"_inbox", ".git", ".obsidian", "_fehler", "__pycache__", "_agent",
                 "node_modules", ".claude"}
        _SKIP_EXT = {".pyc", ".log", ".pid", ".bin"}
        files = []
        for f in sorted(VAULT.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(VAULT)
            parts = rel.parts
            if any(p in _SKIP or p.startswith(".") for p in parts):
                continue
            if f.suffix.lower() in _SKIP_EXT:
                continue
            files.append({
                "path": str(rel).replace("\\", "/"),
                "name": f.name,
                "size": f.stat().st_size,
                "url": "/files/" + str(rel).replace("\\", "/"),
            })
        self.json_response({"files": files})

    def _handle_upload(self):
        """Datei empfangen, in _inbox/ ablegen, sofort verarbeiten und indexieren."""
        try:
            ctype = self.headers.get("Content-Type", "")
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)

            # Boundary aus Content-Type extrahieren
            m = re.search(r'boundary=([^\s;]+)', ctype)
            if not m:
                self.json_response({"error": "no boundary"}, 400)
                return
            boundary = m.group(1).strip('"').encode()

            # Multipart manuell parsen (kein cgi.FieldStorage)
            for part in raw.split(b"--" + boundary)[1:]:
                if part.strip() in (b"--", b""):
                    continue
                sep = part.find(b"\r\n\r\n")
                if sep == -1:
                    continue
                headers_raw = part[:sep].decode("utf-8", errors="replace")
                body = part[sep + 4:]
                if body.endswith(b"\r\n"):
                    body = body[:-2]

                fn_m = re.search(r'filename="([^"]+)"', headers_raw)
                if not fn_m:
                    continue

                filename = Path(fn_m.group(1)).name
                inbox_path = VAULT / "_inbox" / filename
                inbox_path.write_bytes(body)

                # Bilder direkt via Claude Vision transkribieren
                img_exts = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
                if Path(filename).suffix.lower() in img_exts:
                    try:
                        import base64
                        b64 = base64.standard_b64encode(body).decode()
                        mt = "image/jpeg" if filename.lower().endswith((".jpg",".jpeg")) else "image/png"
                        vision_result = ANTHROPIC.messages.create(
                            model="claude-sonnet-5",
                            max_tokens=2000,
                            messages=[{"role": "user", "content": [
                                {"type": "image", "source": {"type": "base64", "media_type": mt, "data": b64}},
                                {"type": "text", "text": "Extrahiere ALLEN Text und ALLE Zahlen/Daten aus diesem Bild. Formatiere als sauberen Markdown-Text. Nichts weglassen."}
                            ]}]
                        )
                        transcription = _response_text(vision_result)
                        # Als .md speichern
                        md_path = VAULT / "_inbox" / (Path(filename).stem + "_vision.md")
                        md_path.write_text(f"# {Path(filename).stem}\n\n{transcription}", encoding="utf-8")
                        inbox_path.unlink(missing_ok=True)  # Original entfernen, .md reicht
                    except Exception:
                        pass  # Normal weiterverarbeiten falls Vision fehlschlägt

                result = run_inbox_and_reindex()
                result["filename"] = filename
                self.json_response(result)
                return

            self.json_response({"error": "Keine Datei im Upload gefunden"}, 400)
        except Exception as ex:
            self.json_response({"error": str(ex)}, 400)

    def do_POST(self):
        if self.path == "/api/auth":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length))
                token = body.get("token", "")
                if token in _AUTH_TOKENS:
                    self.json_response({"ok": True})
                else:
                    self.json_response({"ok": False}, 401)
            except Exception as ex:
                self.json_response({"ok": False, "error": str(ex)}, 400)
            return
        # Alle anderen POST-Endpoints brauchen Auth
        if not _check_auth(self):
            self.json_response({"error": "unauthorized"}, 401)
            return
        if self.path == "/api/chat":
            self.handle_chat()
        elif self.path == "/api/inbox_process":
            result = run_inbox_and_reindex()
            self.json_response(result)
        elif self.path == "/api/upload":
            self._handle_upload()
        elif self.path == "/api/remember":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length))
                self.json_response(api_remember(body.get("text", "")))
            except Exception as ex:
                self.json_response({"error": str(ex)}, 400)
        elif self.path == "/api/linkedin/direction":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length))
                self.json_response(api_linkedin_direction(body.get("prompt", "")))
            except Exception as ex:
                self.json_response({"error": str(ex)}, 400)
        elif self.path == "/api/linkedin/generate-posts":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length)) if length else {}
                self.json_response(api_linkedin_generate_posts(body.get("spec", "")))
            except Exception as ex:
                self.json_response({"error": str(ex)}, 400)
        elif self.path == "/api/linkedin/generate-ideas":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length)) if length else {}
                self.json_response(api_linkedin_generate_ideas(body.get("focus", "")))
            except Exception as ex:
                self.json_response({"error": str(ex)}, 400)
        elif self.path == "/api/buffer/push":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length)) if length else {}
                self.json_response(api_buffer_push(body.get("path")))
            except Exception as ex:
                self.json_response({"error": str(ex)}, 400)
        elif self.path == "/api/buffer/status":
            _cache.pop("buffer_status", None)  # Immer frisch
            self.json_response(api_buffer_status())
        elif self.path.startswith("/api/gmail/download/"):
            msg_id = self.path.split("/api/gmail/download/", 1)[1].strip("/")
            self.json_response(api_gmail_download_attachments(msg_id))
        elif self.path == "/api/vault/create":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length))
                self.json_response(vault_create_folder(body.get("path", "")))
            except Exception as ex:
                self.json_response({"error": str(ex)}, 400)
        elif self.path == "/api/vault/move":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length))
                self.json_response(vault_move(body.get("from", ""), body.get("to", "")))
            except Exception as ex:
                self.json_response({"error": str(ex)}, 400)
        elif self.path == "/api/vault/rename":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length))
                self.json_response(vault_rename(body.get("path", ""), body.get("new_name", "")))
            except Exception as ex:
                self.json_response({"error": str(ex)}, 400)
        elif self.path == "/api/vault/reorganize":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length))
                instructions = body.get("instructions", "")
                plan_result = api_vault_reorganize(instructions)
                if plan_result.get("ok") and body.get("execute", False):
                    exec_result = execute_vault_plan(plan_result["plan"])
                    plan_result["executed"] = exec_result
                self.json_response(plan_result)
            except Exception as ex:
                self.json_response({"error": str(ex)}, 400)
        elif self.path == "/api/tasks/add":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length))
                self.json_response(api_task_add(body.get("text", "")))
            except Exception as ex:
                self.json_response({"error": str(ex)}, 400)
        elif self.path == "/api/tasks/toggle":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length))
                self.json_response(api_task_toggle(body.get("text", ""), bool(body.get("done"))))
            except Exception as ex:
                self.json_response({"error": str(ex)}, 400)
        elif self.path == "/api/tasks/delete":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length))
                self.json_response(api_task_delete(body.get("text", "")))
            except Exception as ex:
                self.json_response({"error": str(ex)}, 400)
        else:
            self.json_response({"error": "not found"}, 404)

    def handle_chat(self):
        # Haiku ist für Chat nicht intelligent genug — Minimum ist Sonnet
        CHAT_MODELS = {
            "claude-sonnet-5",
            "claude-opus-4-8",
        }
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            messages = body.get("messages", [])
            model = body.get("model", "claude-sonnet-5")
            if model not in CHAT_MODELS:
                model = "claude-sonnet-5"  # Haiku → Sonnet upgrade
            if not messages:
                self.json_response({"error": "no messages"}, 400)
                return
        except Exception as ex:
            self.json_response({"error": str(ex)}, 400)
            return

        self.cors_headers(200, "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        last_msg = messages[-1].get("content", "") if messages else ""
        threading.Thread(target=log_turn, args=("user", last_msg), daemon=True).start()

        try:
            from concurrent.futures import ThreadPoolExecutor
            # Alle Kontext-Quellen parallel sammeln
            with ThreadPoolExecutor(max_workers=6) as ex:
                f_system   = ex.submit(build_system)
                f_cust     = ex.submit(get_customer_context, last_msg)
                f_rag      = ex.submit(rag_search, last_msg)
                f_mentioned= ex.submit(get_mentioned_files, messages)
                f_namesearch = ex.submit(search_vault_by_name, last_msg, messages[:-1])
                system     = f_system.result()
                cust_ctx   = f_cust.result()
                rag_ctx    = f_rag.result()
                mentioned_ctx = f_mentioned.result()
                namesearch_ctx = f_namesearch.result()

            # Synthese-Schritt: Haiku erkennt Verbindungen zwischen den Daten
            all_raw = "\n\n".join(filter(None, [cust_ctx, rag_ctx, mentioned_ctx, namesearch_ctx]))
            if all_raw:
                synthesis = synthesize_context(last_msg, all_raw)
                if synthesis:
                    system += f"\n\n=== KONTEXT-ANALYSE: VERBINDUNGEN & SCHLÜSSELINFORMATIONEN ===\n{synthesis}"

            # Kontext einfügen — Direkttreffer zuerst (höchste Priorität)
            if mentioned_ctx:
                system += f"\n\n=== DIREKT REFERENZIERTE DATEIEN ===\n{mentioned_ctx}"
            if namesearch_ctx:
                system += f"\n\n=== NAMENS-SUCHE: GEFUNDENE DOKUMENTE ===\n{namesearch_ctx}"
            if cust_ctx:
                system += f"\n\n=== KUNDEN-AKTEN (vollständig) ===\n{cust_ctx}"
            if rag_ctx:
                system += f"\n\n=== RELEVANTE DOKUMENTE & E-MAILS ===\n{rag_ctx}"

            # Token-Budget: Opus bekommt immer max, Sonnet bei komplexen Anfragen mehr
            COMPLEX_KEYWORDS = {"analysiere", "analyse", "erkläre", "strategie", "warum",
                                 "plane", "vergleich", "bewerte", "empfehlung", "überblick",
                                 "zusammenfassung", "was fehlt", "nächste schritte"}
            is_complex = (any(kw in last_msg.lower() for kw in COMPLEX_KEYWORDS)
                          or len(last_msg) > 250 or model == "claude-opus-4-8")
            max_tok = 16000 if model == "claude-opus-4-8" else (8192 if is_complex else 4096)

            def _send_chunk(text: str):
                payload = json.dumps({"chunk": text}, ensure_ascii=False)
                self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                self.wfile.flush()

            # ── Tool-Use-Loop ──────────────────────────────────────────────────
            # Claude bekommt echte Tools (TOOLS-Schema) statt Text-Signalen. Solange
            # die Antwort mit stop_reason "tool_use" endet: Tool ausführen, Ergebnis als
            # tool_result zurückschicken, Claude erneut anfragen — bis es fertig ist.
            current_messages = list(messages)
            all_text_parts = []
            tasks_changed = False
            MAX_TOOL_ITERATIONS = 8

            for _iteration in range(MAX_TOOL_ITERATIONS):
                with ANTHROPIC.messages.stream(
                    model=model,
                    max_tokens=max_tok,
                    system=system,
                    messages=current_messages,
                    tools=TOOLS,
                ) as stream:
                    for chunk in stream.text_stream:
                        all_text_parts.append(chunk)
                        _send_chunk(chunk)
                    final_message = stream.get_final_message()

                current_messages.append({
                    "role": "assistant",
                    "content": [block.model_dump() for block in final_message.content],
                })

                if final_message.stop_reason != "tool_use":
                    break

                tool_result_blocks = []
                for block in final_message.content:
                    if block.type != "tool_use":
                        continue
                    if block.name in _TASK_TOOL_NAMES:
                        tasks_changed = True
                    result_text, is_error = execute_tool(block.name, block.input, send_chunk=_send_chunk)
                    tool_result_blocks.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_text,
                        "is_error": is_error,
                    })
                current_messages.append({"role": "user", "content": tool_result_blocks})
            else:
                _send_chunk("\n\n---\n*Hinweis: Maximale Anzahl an Tool-Aufrufen erreicht.*")

            response_text = "".join(all_text_parts)
            threading.Thread(target=log_turn, args=("assistant", response_text), daemon=True).start()

            # Nach Task-Änderung: Frontend-Refresh-Event senden
            if tasks_changed:
                payload = json.dumps({"tasks_updated": True})
                self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                self.wfile.flush()

            # Korrekturen im Hintergrund (nur Logging, kein User-Feedback nötig)
            threading.Thread(target=auto_remember, args=(last_msg, response_text), daemon=True).start()
        except Exception as ex:
            payload = json.dumps({"error": str(ex)})
            self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))

        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


class ThreadedServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def _prewarm_cache():
    """Gmail + Kalender im Hintergrund vorladen damit die Sidebar sofort Daten hat."""
    import time
    time.sleep(2)  # kurz warten bis Server bereit
    try:
        api_gmail()
        print("  Cache: Gmail vorgeladen")
    except Exception as e:
        print(f"  Cache: Gmail-Fehler {e}")
    try:
        api_calendar()
        print("  Cache: Kalender vorgeladen")
    except Exception as e:
        print(f"  Cache: Kalender-Fehler {e}")
    try:
        api_buffer_status()
    except Exception:
        pass


if __name__ == "__main__":
    server = ThreadedServer(("localhost", PORT), Handler)
    print(f"\n✓ Prozessia Brain Server: http://localhost:{PORT}")
    print(f"  Gmail:   {'✓ verbunden' if GMAIL_OK else '✗ nicht verbunden'}")
    print(f"  Outlook: {'✓ verbunden' if OUTLOOK_OK else '✗ nicht verbunden'}")
    print("  Ctrl+C zum Beenden.\n")
    threading.Thread(target=_prewarm_cache, daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer gestoppt.")
