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
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from pathlib import Path
from datetime import datetime, timedelta

VAULT = Path.home() / "Documents" / "Prozessia-Brain"
sys.path.insert(0, str(VAULT / "_agent"))
PORT = 3001
AUTOPOSTER = VAULT / "_inbox" / "Branding" / "claude-linkedin-auto-poster"

import anthropic
ANTHROPIC = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

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
    """Dateipfade die im Gesprächsverlauf erwähnt wurden direkt einlesen und einfügen."""
    all_text = " ".join(m.get("content", "") for m in messages[-12:])
    # Dateipfade erkennen: relative Pfade mit / und Dateiendung
    paths = re.findall(r'[A-Za-z_][A-Za-z0-9_\-/. ]+\.(?:md|txt|json|html)', all_text)
    results = []
    seen = set()
    for raw_p in paths:
        p = raw_p.strip()
        if p in seen or len(p) < 5:
            continue
        seen.add(p)
        full = VAULT / p
        if full.exists() and full.is_file():
            try:
                content = full.read_text(errors="ignore")[:4000]
                results.append(f"[DATEI DIREKT GELESEN: {p}]\n{content}")
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
        return result.content[0].text.strip()
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
    """Alle .md-Dateien die noch nicht in FAISS sind sofort hinzufügen."""
    if _rag_meta is None or _rag_model is None:
        return 0
    existing = {(m.get("path", "") if isinstance(m, dict) else str(m)) for m in _rag_meta}
    added = 0
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
                added += 1
        except Exception:
            pass
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
    combined = (sender + " " + subject + " " + body[:500]).lower()
    if any(d in combined for d in CUSTOMER_DOMAINS):
        return True
    if any(k in combined for k in IMPORTANT_KEYWORDS):
        return True
    return False

def _auto_memory_from_email(sender: str, subject: str, body: str):
    try:
        prompt = f"""Analysiere diese E-Mail und extrahiere NUR dauerhaft wichtige Informationen für Sebastian Spuhler (Prozessia GbR).

Wichtig: neue Aufträge, Preise, Deadlines, Kundenwünsche, Zusagen, Absagen, konkrete nächste Schritte.
Nicht wichtig: Newsletters, allgemeine Anfragen, Spam, automatische Bestätigungen.

Von: {sender}
Betreff: {subject}
Inhalt: {body[:600]}

Antworte NUR mit JSON (kein Markdown):
{{"items": [{{"kategorie": "KONTEXT", "fakt": "kurze Aussage auf Deutsch"}}]}}
Kategorien: KONTEXT, PROZESS, KORREKTUR
Wenn nichts Wichtiges: {{"items": []}}"""

        result = ANTHROPIC.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        text = result.content[0].text.strip()
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if not m:
            return
        data = json.loads(m.group())
        for item in data.get("items", []):
            kat = item.get("kategorie", "KONTEXT").upper()
            fakt = item.get("fakt", "").strip()
            if fakt:
                _append_to_memory(kat, f"[Email: {subject[:50]}] {fakt}")
    except Exception:
        pass

_DEEP_SCAN_DONE_PATH = EMAIL_CACHE_DIR / "deep_scan_done.flag"

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
        "Nutze fließenden Text wenn möglich. Tabellen und Listen nur wenn sie echten Mehrwert bieten (mindestens 3 vergleichbare Punkte, niemals für einfache Antworten).",
        "Zeige Initiative: Wenn du beim Lesen der Dokumente etwas Relevantes siehst das Sebastian nicht explizit gefragt hat, bringe es trotzdem ein — kurz und direkt.",
        "Verbinde Punkte: Wenn eine E-Mail zu einer Aufgabe in context.md passt oder ein Angebot zu einer Bestellung, sage das aktiv.",
        "Sei konkret: Nenne immer exakte Zahlen, Daten, Namen aus den Dokumenten. Nie schätzen wenn die Daten vorhanden sind.",
        "Wenn etwas fehlt, sage klar was fehlt und warum — kein Herumreden.",
        "",
        "FAKTEN & DATEN:",
        "Wenn du Zahlen oder Fakten aus Dokumenten nennst, zitiere die Quelle (Dateiname oder 'laut Angebot AG0024').",
        "Erfinde NIEMALS Zahlen oder schätze ('ca.') wenn du die echten Daten im Vault hast.",
        "Bei Preisen, Terminen, Vertragsinhalten: immer direkt aus dem Dokument.",
        "",
        "ZUGRIFF:",
        "Du hast ECHTZEIT-Zugriff auf Gmail, Outlook-Kalender, den gesamten Vault und alle indizierten E-Mails.",
        "Sage NIEMALS 'kein Zugriff' oder 'Inhalt nicht verfügbar' — alle Dateien stehen dir zur Verfügung.",
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

    # Kalender live einlesen
    try:
        if OUTLOOK_OK:
            events = api_calendar()
            if events:
                cal_lines = ["=== OUTLOOK-KALENDER (nächste 14 Tage) ==="]
                for e in events[:12]:
                    cal_lines.append(f"  {e.get('date','')} {e.get('time','')} — {e.get('title','')} {('('+e['location']+')') if e.get('location') else ''}")
                parts += ["\n".join(cal_lines), ""]
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
                    mail_lines.append(f"  {unread} [{m.get('time','')}] {m.get('from','')} <{m.get('email','')}> — {m.get('subject','')}{preview}")
                parts += ["\n".join(mail_lines), ""]
    except Exception:
        pass

    # LinkedIn: geplante Beiträge + Ideen live einlesen
    try:
        li_posts = api_linkedin_posts()
        li_ideas = api_linkedin_ideas()
        li_dir_path = AUTOPOSTER / "brain-direction.md"
        li_section = [f"=== LINKEDIN AUTOPOSTER (Stand: {li_posts.get('datum','?')}) ==="]
        if li_posts.get("posts"):
            li_section.append("Geplante Beiträge:")
            for p in li_posts["posts"]:
                li_section.append(f"  - {p['tag']} {p['termin'][:10]}: {p['idee']}")
        else:
            li_section.append("Geplante Beiträge: keine in der Pipeline")
        if li_ideas.get("ideen"):
            li_section.append(f"\nGenerierte Ideen ({li_ideas.get('datum','?')}, alle {len(li_ideas['ideen'])} Ideen):")
            for i in li_ideas["ideen"]:
                li_section.append(f"  - [{i['kategorie']}] {i['titel']} | Hook: {i['hook']} | Format: {i['format']} | CTA: {i['cta']}")
        if li_dir_path.exists():
            direction_text = li_dir_path.read_text(encoding="utf-8")
            match = re.search(r"## Aktuelle Richtung\n\n(.+?)(?:\n---|\Z)", direction_text, re.DOTALL)
            if match:
                li_section.append(f"\nAktuelle Richtungsvorgabe: {match.group(1).strip()}")
        li_section.append("\nWICHTIG – Aktions-Signale (immer am Ende der Antwort, auf einer eigenen Zeile):")
        li_section.append("  Wenn Sebastian neue Ideen möchte → [GENERATE_IDEAS: fokus]")
        li_section.append("  Wenn Sebastian Posts ausgeschrieben haben möchte → schreibe NICHT den Text selbst,")
        li_section.append("  sondern benutze NUR das Signal: [GENERATE_POSTS: Thema1/Datum1, Thema2/Datum2, Zielgruppe]")
        li_section.append("  Das Signal löst den Backend-Generator aus der die Posts korrekt formatiert und speichert.")
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
                start_raw = e.get("start", {}).get("dateTime", "")
                end_raw   = e.get("end",   {}).get("dateTime", "")
                try:
                    # Python 3.9 fromisoformat kann keine 7-stelligen Mikrosekunden
                    # oder Timezone-Suffix → auf 19 Zeichen kürzen
                    start_dt = datetime.fromisoformat(start_raw[:19])
                    end_dt   = datetime.fromisoformat(end_raw[:19])
                    if start_dt < datetime.now() - timedelta(hours=1):
                        continue
                    events.append({
                        "title":    e.get("subject", ""),
                        "start":    start_dt.strftime("%Y-%m-%dT%H:%M"),
                        "end":      end_dt.strftime("%Y-%m-%dT%H:%M"),
                        "location": e.get("location", {}).get("displayName", ""),
                        "allDay":   e.get("isAllDay", False),
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

def api_tasks():
    try:
        ctx = (VAULT / "_agent" / "context.md").read_text()
        tasks = []
        for line in ctx.splitlines():
            if "- [ ]" in line:
                text = line.replace("- [ ]", "").strip()
                # Detect urgency by date
                m = re.search(r'(\d{1,2})\.(\d{1,2})\.', text)
                urgency = "normal"
                if m:
                    try:
                        day, month = int(m.group(1)), int(m.group(2))
                        dt = datetime(2026, month, day)
                        days_left = (dt - datetime.now()).days
                        if days_left <= 7:
                            urgency = "urgent"
                        elif days_left <= 21:
                            urgency = "soon"
                    except Exception:
                        pass
                tasks.append({"text": text, "urgency": urgency})
            elif "- [x]" in line or "- [X]" in line:
                text = line.replace("- [x]", "").replace("- [X]", "").strip()
                tasks.append({"text": text, "urgency": "done", "done": True})
        return tasks
    except Exception:
        return []

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
    path = _latest_autoposter_file("ideen")
    if not path:
        return {"ideen": [], "datum": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        result = {
            "datum": data.get("generiert_am", "")[:10],
            "ideen": [
                {
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
    path = _latest_autoposter_file("beitraege")
    if not path:
        return {"posts": [], "datum": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        posts = []
        for key in ["donnerstag", "freitag", "montag", "dienstag", "mittwoch"]:
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

def api_linkedin_generate_ideas(focus: str = "") -> dict:
    direction_path = AUTOPOSTER / "brain-direction.md"
    current_direction = ""
    if direction_path.exists():
        match = re.search(r"## Aktuelle Richtung\n\n(.+?)(?:\n---|\Z)",
                          direction_path.read_text(encoding="utf-8"), re.DOTALL)
        if match:
            current_direction = match.group(1).strip()

    prompt = f"""Du bist LinkedIn-Content-Stratege für Prozessia (KI-Automatisierung für produzierende KMU, 20–80 MA, DACH).
Zielgruppe: Einkaufsleiter, Produktionsleiter, Geschäftsführer im Mittelstand.
Themen: KI-Beschaffung, Automatisierung, EU AI Act, Produktivität, Mittelstand.

{f"Richtungsvorgabe von Sebastian: {current_direction}" if current_direction else ""}
{f"Zusätzlicher Fokus: {focus}" if focus else ""}

Generiere genau 10 LinkedIn-Ideen als JSON. Jede Idee muss enthalten:
- kategorie: "Einkauf" | "Industrie" | "Compliance" | "KI-Tipp" | "Kundenstory"
- branche: z.B. "Maschinenbau", "Allgemein", "Werkzeugbau"
- titel: prägnanter Titel (max 60 Zeichen)
- hook: erste Zeile des Posts — neugierig machend (max 80 Zeichen)
- kern_botschaft: was der Leser mitnimmt
- zielgruppe_spezifisch: konkrete Persona (z.B. "Einkaufsleiter Werkzeugbau, 60 MA")
- format_empfehlung: "Text" | "Karussell" | "Liste" | "Story"
- cta_vorschlag: Abschlussfrage oder Call-to-Action

Antworte NUR mit validem JSON, kein Markdown drumherum:
{{"generiert_am": "ISO-DATUM", "anzahl": 10, "ideen": [...]}}"""

    try:
        result = ANTHROPIC.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        text = result.content[0].text.strip()
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if not match:
            return {"error": "Kein JSON in Antwort"}
        data = json.loads(match.group())
        data["generiert_am"] = datetime.now().isoformat()
        data["anzahl"] = len(data.get("ideen", []))

        out_path = AUTOPOSTER / "output" / f"ideen-{datetime.now().strftime('%Y-%m-%d')}.json"
        out_path.parent.mkdir(exist_ok=True)
        out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

        # Cache invalidieren damit neue Ideen sofort sichtbar sind
        _cache.pop("li_ideas", None)

        return {"ok": True, "anzahl": data["anzahl"], "ideen": [
            {"titel": i.get("titel",""), "hook": i.get("hook",""),
             "kategorie": i.get("kategorie",""), "format": i.get("format_empfehlung",""),
             "cta": i.get("cta_vorschlag","")}
            for i in data.get("ideen", [])
        ]}
    except Exception as e:
        return {"error": str(e)}

def api_linkedin_generate_posts(spec: str) -> dict:
    """Schreibt fertige LinkedIn Post-Texte basierend auf Spec und speichert sie."""
    direction_path = AUTOPOSTER / "brain-direction.md"
    current_direction = ""
    if direction_path.exists():
        m = re.search(r"## Aktuelle Richtung\n\n(.+?)(?:\n---|\Z)",
                      direction_path.read_text(encoding="utf-8"), re.DOTALL)
        if m:
            current_direction = m.group(1).strip()

    prompt = f"""Du bist LinkedIn-Texter für Prozessia (KI-Automatisierung für produzierende KMU, 20–80 MA, DACH).
Zielgruppe: Einkaufsleiter, Produktionsleiter, Geschäftsführer im Mittelstand.
Stil: sachlich, direkt, keine leeren Phrasen, kein "In der heutigen Zeit". Mit konkreten Zahlen.
Max. 1.200 Zeichen pro Post. Keine Emojis außer 1–2 sparsam. Hashtags am Ende (3–5).

{f"Richtungsvorgabe: {current_direction}" if current_direction else ""}

Spezifikation für die Posts:
{spec}

Schreibe jeden Post vollständig aus. Antworte NUR mit validem JSON:
{{
  "generiert_am": "ISO-DATUM",
  "posts": [
    {{
      "tag": "Dienstag",
      "datum": "YYYY-MM-DD",
      "thema": "Themenname",
      "text": "Vollständiger Post-Text fertig zum Kopieren"
    }}
  ]
}}"""

    try:
        result = ANTHROPIC.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=6000,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = result.content[0].text.strip()

        # Robust: Posts als Blöcke parsen falls JSON kaputt
        posts = []
        # Versuche zuerst sauberes JSON
        try:
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                data = json.loads(match.group())
                posts = data.get("posts", [])
        except Exception:
            pass

        # Fallback: strukturierte Extraktion aus Text
        if not posts:
            blocks = re.split(r'\n#+\s+', raw)
            for block in blocks:
                day_match = re.search(r'(Montag|Dienstag|Mittwoch|Donnerstag|Freitag)', block, re.IGNORECASE)
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', block)
                if day_match and date_match:
                    posts.append({
                        "tag": day_match.group(1),
                        "datum": date_match.group(1),
                        "thema": block.split('\n')[0].strip()[:80],
                        "text": block.strip()[:1500],
                    })

        if not posts:
            return {"error": "Keine Posts extrahiert", "raw": raw[:500]}

        # Speichern
        out_data = {"generiert_am": datetime.now().isoformat(), "kanaele": [], "planungen": []}
        for p in posts:
            key = p.get("tag", "").lower()
            out_data[key] = {
                "termin": f"{p.get('datum','')}T09:30:00+02:00",
                "idee": p.get("thema", ""),
                "text": p.get("text", ""),
            }
        out_path = AUTOPOSTER / "output" / f"beitraege-{datetime.now().strftime('%Y-%m-%d')}.json"
        out_path.parent.mkdir(exist_ok=True)
        out_path.write_text(json.dumps(out_data, ensure_ascii=False, indent=2), encoding="utf-8")
        _cache.pop("li_posts", None)
        return {"ok": True, "posts": posts}
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

SPEICHERN:
- Korrekturen (Sebastian sagt etwas ist falsch/anders) → KORREKTUR
- Neue Fakten: Preise, Vertragsinhalte, Deadlines, Entscheidungen → KONTEXT
- Arbeitsregeln und Präferenzen von Sebastian → REGEL
- Neue Abläufe oder Prozessentscheidungen → PROZESS

NICHT SPEICHERN:
- Reine Informationsabfragen ohne neuen Fakt
- Dinge die Brain schon weiß (kein Duplikat)
- Operationelle Kleinstdetails (E-Mail-Snippets, Aufzählungen)

Sebastian: {user_msg[:800]}

Brain: {assistant_msg[:400]}

JSON-Antwort (kein Markdown):
{{"items": [{{"kategorie": "KORREKTUR", "fakt": "präzise Aussage"}}]}}
Max 3 Items. Wenn nichts Neues: {{"items": []}}"""

        result = ANTHROPIC.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        text = result.content[0].text.strip()
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if not match:
            return
        data = json.loads(match.group())
        saved = []
        for item in data.get("items", []):
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
                            model="claude-sonnet-4-6",
                            max_tokens=2000,
                            messages=[{"role": "user", "content": [
                                {"type": "image", "source": {"type": "base64", "media_type": mt, "data": b64}},
                                {"type": "text", "text": "Extrahiere ALLEN Text und ALLE Zahlen/Daten aus diesem Bild. Formatiere als sauberen Markdown-Text. Nichts weglassen."}
                            ]}]
                        )
                        transcription = vision_result.content[0].text
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
        else:
            self.json_response({"error": "not found"}, 404)

    def handle_chat(self):
        # Haiku ist für Chat nicht intelligent genug — Minimum ist Sonnet
        CHAT_MODELS = {
            "claude-sonnet-4-6",
            "claude-opus-4-8",
        }
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            messages = body.get("messages", [])
            model = body.get("model", "claude-sonnet-4-6")
            if model not in CHAT_MODELS:
                model = "claude-sonnet-4-6"  # Haiku → Sonnet upgrade
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
            with ThreadPoolExecutor(max_workers=5) as ex:
                f_system   = ex.submit(build_system)
                f_cust     = ex.submit(get_customer_context, last_msg)
                f_rag      = ex.submit(rag_search, last_msg)
                f_mentioned= ex.submit(get_mentioned_files, messages)
                system     = f_system.result()
                cust_ctx   = f_cust.result()
                rag_ctx    = f_rag.result()
                mentioned_ctx = f_mentioned.result()

            # Synthese-Schritt: Haiku erkennt Verbindungen zwischen den Daten
            all_raw = "\n\n".join(filter(None, [cust_ctx, rag_ctx, mentioned_ctx]))
            if all_raw:
                synthesis = synthesize_context(last_msg, all_raw)
                if synthesis:
                    system += f"\n\n=== KONTEXT-ANALYSE: VERBINDUNGEN & SCHLÜSSELINFORMATIONEN ===\n{synthesis}"

            # Kontext einfügen (nach Synthese, damit Hauptmodell beides hat)
            if mentioned_ctx:
                system += f"\n\n=== DIREKT REFERENZIERTE DATEIEN ===\n{mentioned_ctx}"
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

            full_response = []
            with ANTHROPIC.messages.stream(
                model=model,
                max_tokens=max_tok,
                system=system,
                messages=messages,
            ) as stream:
                for chunk in stream.text_stream:
                    full_response.append(chunk)
                    payload = json.dumps({"chunk": chunk}, ensure_ascii=False)
                    self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                    self.wfile.flush()

            response_text = "".join(full_response)
            threading.Thread(target=log_turn, args=("assistant", response_text), daemon=True).start()

            # Korrekturen sofort bestätigen — Brain meldet was es gelernt hat
            def remember_and_confirm(u, a):
                saved = auto_remember(u, a)
                if saved:
                    note = "\n\n---\n*Notiert: " + " | ".join(saved[:2]) + "*"
                    payload = json.dumps({"chunk": note}, ensure_ascii=False)
                    try:
                        self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                        self.wfile.flush()
                    except Exception:
                        pass
            threading.Thread(target=remember_and_confirm, args=(last_msg, response_text), daemon=True).start()
        except Exception as ex:
            payload = json.dumps({"error": str(ex)})
            self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))

        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


class ThreadedServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


if __name__ == "__main__":
    server = ThreadedServer(("localhost", PORT), Handler)
    print(f"\n✓ Prozessia Brain Server: http://localhost:{PORT}")
    print(f"  Gmail:   {'✓ verbunden' if GMAIL_OK else '✗ nicht verbunden'}")
    print(f"  Outlook: {'✓ verbunden' if OUTLOOK_OK else '✗ nicht verbunden'}")
    print("  Ctrl+C zum Beenden.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer gestoppt.")
