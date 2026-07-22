"""System-Prompt-Aufbau für den Chat. Migriert aus brain_server.py
(vault_tree, build_system, get_customer_context, get_mentioned_files,
synthesize_context)."""
import re
from datetime import datetime, timedelta
from pathlib import Path

from app.config import get_settings
from app.constants import Models
from app.services import calendar_service, linkedin_service, mail_service
from app.services.anthropic_client import get_client, get_response_text

_SKIP_TREE = {
    ".git", ".obsidian", "__pycache__", ".DS_Store", "node_modules",
    # App-Code/interne Verzeichnisse - kein Vault-Inhalt, gehören nicht in die
    # Struktur-Übersicht, die bei jeder Chat-Anfrage mitgeschickt wird (siehe
    # Token-Analyse 2026-07-17: die ungefilterte Tiefe-3-Baumdarstellung kostete
    # ~10.400 von ~15.100 Tokens des Basis-System-Prompts, u.a. weil sie
    # Dateinamen aus _agent/ wie drive_token.json/gmail_token.json/
    # ms_token_cache.bin mit auflistete). Deckt sich mit dem _SKIP-Set in
    # files.py (Datei-Browser) und SKIP_DIRS in classify.py/rag.py.
    "_agent", "_inbox", "_fehler", "backend", "frontend", "services",
    "mcp-vnc", ".claude", ".venv",
}


def vault_tree(max_depth: int = 2) -> str:
    settings = get_settings()
    lines = ["Prozessia-Brain/"]

    def _walk(path: Path, prefix: str, depth: int):
        if depth > max_depth:
            return
        try:
            entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except PermissionError:
            return
        entries = [e for e in entries if e.name not in _SKIP_TREE and not e.name.startswith(".")]
        for i, entry in enumerate(entries[:60]):
            connector = "└── " if i == len(entries) - 1 else "├── "
            lines.append(f"{prefix}{connector}{entry.name}{'/' if entry.is_dir() else ''}")
            if entry.is_dir():
                ext = "    " if i == len(entries) - 1 else "│   "
                _walk(entry, prefix + ext, depth + 1)

    _walk(settings.vault_path, "", 1)
    return "\n".join(lines)


def get_mentioned_files(messages: list[dict]) -> str:
    """Dateipfade die im Gesprächsverlauf erwähnt wurden direkt einlesen."""
    settings = get_settings()
    all_text = " ".join(m.get("content", "") for m in messages[-12:])
    paths = re.findall(r"[A-Za-z_][A-Za-z0-9_\-/. ]+\.(?:md|txt|json|html)", all_text)
    results = []
    seen: set[str] = set()
    for raw_p in paths:
        p = raw_p.strip()
        if p in seen or len(p) < 5:
            continue
        seen.add(p)
        full = settings.vault_path / p
        if full.exists() and full.is_file():
            try:
                content = full.read_text(encoding="utf-8", errors="ignore")[:4000]
                results.append(f"[DATEI DIREKT GELESEN: {p}]\n{content}")
            except Exception:
                pass
    return "\n\n".join(results)


def get_customer_context(query: str) -> str:
    """Wenn ein Kundenname im Query vorkommt, alle seine Dateien direkt einfügen."""
    settings = get_settings()
    customer_dir = settings.vault_path / "Kunden"
    if not customer_dir.exists():
        return ""
    q_lower = query.lower()
    results = []
    for cust_path in customer_dir.iterdir():
        if not cust_path.is_dir():
            continue
        name_parts = [p for p in re.split(r"[\s_\-]+", cust_path.name.lower()) if len(p) > 3]
        if not any(part in q_lower for part in name_parts):
            continue
        for f in sorted(cust_path.rglob("*.md"))[:8]:
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")[:2000]
                results.append(f"[{f.relative_to(settings.vault_path)}]\n{content}")
            except Exception:
                pass
    return "\n\n".join(results)


def synthesize_context(query: str, raw_context: str) -> str:
    """Haiku analysiert Verbindungen zwischen Daten-Stücken -> Kontext-Landkarte."""
    if not raw_context or len(raw_context) < 400:
        return ""
    try:
        prompt = f"""Du bist ein Kontext-Analyst. Sebastians Frage: "{query[:250]}"

Analysiere die unten stehenden Daten-Fragmente und erkläre in 4-6 präzisen Bullet Points:
- Welche Mails, Dokumente und Aufgaben hängen direkt zusammen?
- Was ist die wichtigste Information zur Beantwortung der Frage?
- Welche zeitlichen oder inhaltlichen Verbindungen gibt es?
- Was fehlt möglicherweise noch?

Sei konkret und nenne Dateinamen/Absender/Daten. Kein Intro, nur Bullet Points.

DATEN:
{raw_context[:3500]}"""
        return complete_json(prompt, model=Models.HAIKU, max_tokens=600).strip()
    except Exception:
        return ""


_BASE_PROMPT = """Du bist das persönliche Second Brain von Sebastian Spuhler (Prozessia GbR, Saarbrücken).
Du hast vollständigen Zugriff auf seinen Vault, alle Kundendaten, Aufgaben, E-Mails und Dokumente.

SCHREIBSTIL:
Schreibe wie ein kluger, direkt informierter Kollege - nicht wie ein Chatbot oder eine KI.
Nutze fließenden Text wenn möglich. Tabellen und Listen nur wenn sie echten Mehrwert bieten (mindestens 3 vergleichbare Punkte, niemals für einfache Antworten).
Zeige Initiative: Wenn du beim Lesen der Dokumente etwas Relevantes siehst das Sebastian nicht explizit gefragt hat, bringe es trotzdem ein - kurz und direkt.
Verbinde Punkte: Wenn eine E-Mail zu einer Aufgabe in context.md passt oder ein Angebot zu einer Bestellung, sage das aktiv.
Sei konkret: Nenne immer exakte Zahlen, Daten, Namen aus den Dokumenten. Nie schätzen wenn die Daten vorhanden sind.
Wenn etwas fehlt, sage klar was fehlt und warum - kein Herumreden.

FAKTEN & DATEN:
Wenn du Zahlen oder Fakten aus Dokumenten nennst, zitiere die Quelle (Dateiname oder 'laut Angebot AG0024').
Erfinde NIEMALS Zahlen oder schätze ('ca.') wenn du die echten Daten im Vault hast.
Bei Preisen, Terminen, Vertragsinhalten: immer direkt aus dem Dokument.

ZUGRIFF:
Du hast ECHTZEIT-Zugriff auf Gmail, Outlook-Kalender, den gesamten Vault und alle indizierten E-Mails.
Sage NIEMALS 'kein Zugriff' oder 'Inhalt nicht verfügbar' - alle Dateien stehen dir zur Verfügung.
Wenn eine E-Mail nur 'anbei das Dokument' enthält ohne Body-Text, erkläre das klar: der Anhang war eine Datei, kein Text.
Wenn Sebastian ein Datum oder eine persönliche Tatsache nennt: glaube ihm sofort, kein Widerspruch.

LERNEN & KORREKTUREN:
Wenn Sebastian dich korrigiert, etwas berichtigt oder dir etwas beibringt: Integriere es sofort in deine Antwort und bestätige es aktiv - sag was du gelernt hast, nicht nur 'danke'.

PROAKTIVE INTELLIGENZ:
Wenn du beim Lesen der Daten etwas siehst das Sebastian wichtig sein könnte - eine überfällige Aufgabe, eine E-Mail die noch keine Antwort hat, ein nahender Termin, eine offene Frage - erwähne es UNGEFRAGT am Ende deiner Antwort in 1-2 Sätzen.
Du bist nicht nur ein Antwortgeber sondern ein aktiver Gedankenpartner. Denke mit."""

_WEEKDAYS_DE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
_WEEKDAYS_SHORT = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def build_system() -> str:
    settings = get_settings()
    now = datetime.now()
    today_str = f"{_WEEKDAYS_DE[now.weekday()]}, {now.strftime('%d.%m.%Y')}"

    monday = now - timedelta(days=now.weekday())
    week_lines = ["Wochentage aktuell:"]
    for i in range(7):
        day = monday + timedelta(days=i)
        marker = " ← HEUTE" if day.date() == now.date() else ""
        week_lines.append(f"  {_WEEKDAYS_SHORT[i]} {day.strftime('%d.%m.%Y')}{marker}")

    parts = [_BASE_PROMPT, f"Heute: {today_str}.", "\n".join(week_lines), ""]

    for label, path, limit in [
        ("PROZESSIA-PROFIL", settings.prozessia_path, 5000),
        ("AKTUELLE AUFGABEN & KONTEXT", settings.context_path, 4000),
        ("GELERNTES & GEDÄCHTNIS", settings.memory_path, 4000),
    ]:
        try:
            parts += [f"=== {label} ===", path.read_text(encoding="utf-8")[:limit], ""]
        except Exception:
            pass

    try:
        parts += ["=== VAULT-ORDNERSTRUKTUR ===", vault_tree(), ""]
    except Exception:
        pass

    try:
        conv_log = _get_recent_conversations()
        if conv_log:
            parts += [conv_log, ""]
    except Exception:
        pass

    try:
        if calendar_service.is_connected():
            events = calendar_service.get_calendar_events()
            if events:
                cal_lines = ["=== OUTLOOK-KALENDER (nächste 14 Tage) ==="]
                for e in events[:12]:
                    loc = f" ({e['location']})" if e.get("location") else ""
                    cal_lines.append(f"  {e.get('start', '')} - {e.get('title', '')}{loc}")
                parts += ["\n".join(cal_lines), ""]
    except Exception:
        pass

    try:
        if mail_service.is_connected():
            mails = mail_service.get_gmail_summary()
            if mails:
                mail_lines = ["=== GMAIL - NEUESTE 20 E-MAILS (Echtzeit) ==="]
                for m in mails[:20]:
                    unread = "●" if m.get("unread") else " "
                    preview = f" | {m.get('snippet', '')}" if m.get("snippet") else ""
                    mail_lines.append(f"  {unread} [{m.get('time', '')}] {m.get('from', '')} <{m.get('email', '')}> - {m.get('subject', '')}{preview}")
                parts += ["\n".join(mail_lines), ""]
    except Exception:
        pass

    try:
        li_posts = linkedin_service.get_posts()
        li_ideas = linkedin_service.get_ideas()
        li_section = [f"=== LINKEDIN AUTOPOSTER (Stand: {li_posts.get('datum', '?')}) ==="]
        if li_posts.get("posts"):
            li_section.append("Geplante Beiträge:")
            for p in li_posts["posts"]:
                li_section.append(f"  - {p['tag']} {p['termin'][:10]}: {p['idee']}")
        else:
            li_section.append("Geplante Beiträge: keine in der Pipeline")
        if li_ideas.get("ideen"):
            li_section.append(f"\nGenerierte Ideen ({li_ideas.get('datum', '?')}, alle {len(li_ideas['ideen'])} Ideen):")
            for i in li_ideas["ideen"]:
                li_section.append(f"  - [{i['kategorie']}] {i['titel']} | Hook: {i['hook']} | Format: {i['format']} | CTA: {i['cta']}")
        direction = linkedin_service._current_direction()
        if direction:
            li_section.append(f"\nAktuelle Richtungsvorgabe: {direction}")
        li_section.append("\nWICHTIG - Aktions-Signale (immer am Ende der Antwort, auf einer eigenen Zeile):")
        li_section.append("  Wenn Sebastian neue Ideen möchte -> [GENERATE_IDEAS: fokus]")
        li_section.append("  Wenn Sebastian Posts ausgeschrieben haben möchte -> schreibe NICHT den Text selbst,")
        li_section.append("  sondern benutze NUR das Signal: [GENERATE_POSTS: Thema1/Datum1, Thema2/Datum2, Zielgruppe]")
        parts += ["\n".join(li_section), ""]
    except Exception:
        pass

    return "\n".join(parts)


def _get_recent_conversations() -> str:
    from app.services.conversations import get_recent_conversations

    return get_recent_conversations()
