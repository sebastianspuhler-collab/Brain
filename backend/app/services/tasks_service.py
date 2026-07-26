"""Aufgabenliste aus context.md. Migriert aus brain_server.py:api_tasks().

Zuständigkeit und Fälligkeitsdatum werden als Tags am Zeilenende gespeichert
(z.B. "@Sebastian !due(2026-07-05)"), damit context.md für Sebastian in Obsidian
weiterhin normal lesbar bleibt. calendar_service liest denselben Parser, damit
ein gesetztes Fälligkeitsdatum automatisch als Kalender-Deadline auftaucht.
Fehlt der @Tag (bestehende Alt-Einträge), gilt die Aufgabe als für beide zuständig.
"""
import re
from datetime import datetime

from app.config import get_settings

ASSIGNEES = ("Amin", "Sebastian", "Beide")
DEFAULT_ASSIGNEE = "Beide"

_ASSIGNEE_TAG_RE = re.compile(r"(?:^|(?<=\s))@(Amin|Sebastian|Beide)(?=\s|$)", re.IGNORECASE)
_DUE_TAG_RE = re.compile(r"(?:^|(?<=\s))!due\((\d{4}-\d{2}-\d{2})\)(?=\s|$)", re.IGNORECASE)
_LEGACY_DATE_RE = re.compile(r"(\d{1,2})\.(\d{1,2})\.")

# Kanban-Board (Umsetzungsplan 2026-07-27): dritter Tag neben @Zuständig und
# !due(...) - nur für offene Aufgaben relevant ("todo"/"in_progress"), erledigt
# bleibt weiterhin allein über die Checkbox gesteuert (kein doppeltes
# Wahrheits-Feld). Fehlt der Tag (bestehende Alt-Einträge), gilt "todo".
STATUS_VALUES = ("todo", "in_progress")
_STATUS_TAG_RE = re.compile(r"(?:^|(?<=\s))!status\((\w+)\)(?=\s|$)", re.IGNORECASE)

# Jira-artige Zusatzfelder (Umsetzungsplan 2026-07-27): Kunde/Kategorie nach
# demselben Tag-Muster wie @Zuständig/!due(...). Beschreibung bewusst NICHT
# als eingerückte Zeile unter der Checkbox (das würde _update_task_line()/
# delete_task() zwingen, Nachbarzeilen zuverlässig einer Aufgabe zuzuordnen -
# fehleranfällig beim Löschen), sondern als eigener !desc[...]-Tag auf
# derselben Zeile (eckige statt runde Klammern, damit Kommas/Punkte im
# Beschreibungstext nicht mit !due(...)/!kunde(...) kollidieren). Einzige
# Einschränkung: keine schließende eckige Klammer "]" im Beschreibungstext.
CATEGORIES = ("Entwicklung", "Buchhaltung", "LinkedIn", "Cold Calls", "Meetings", "Administration", "Sonstiges")
_KUNDE_TAG_RE = re.compile(r"(?:^|(?<=\s))!kunde\(([^)]*)\)(?=\s|$)", re.IGNORECASE)
_KATEGORIE_TAG_RE = re.compile(r"(?:^|(?<=\s))!kategorie\(([^)]*)\)(?=\s|$)", re.IGNORECASE)
_DESC_TAG_RE = re.compile(r"(?:^|(?<=\s))!desc\[([^\]]*)\](?=\s|$)", re.IGNORECASE)


def _strip_checkbox(line: str) -> str | None:
    """Gibt den Aufgabentext (inkl. Tags) ohne Checkbox-Präfix zurück, oder None."""
    if "- [ ]" in line:
        return line.replace("- [ ]", "").strip()
    if "- [x]" in line or "- [X]" in line:
        return line.replace("- [x]", "").replace("- [X]", "").strip()
    return None


def _split_tags(raw_text: str) -> tuple[str, str, str | None, str, str | None, str | None, str]:
    """Trennt @Zuständig-, !due(...)-, !status(...)-, !kunde(...)-,
    !kategorie(...)- und !desc[...]-Tags vom Aufgabentext."""
    due = None
    m = _DUE_TAG_RE.search(raw_text)
    if m:
        due = m.group(1)
        raw_text = (raw_text[: m.start()] + raw_text[m.end() :]).strip()

    status = "todo"
    m = _STATUS_TAG_RE.search(raw_text)
    if m and m.group(1).lower() in STATUS_VALUES:
        status = m.group(1).lower()
        raw_text = (raw_text[: m.start()] + raw_text[m.end() :]).strip()

    kunde = None
    m = _KUNDE_TAG_RE.search(raw_text)
    if m:
        kunde = m.group(1) or None
        raw_text = (raw_text[: m.start()] + raw_text[m.end() :]).strip()

    kategorie = None
    m = _KATEGORIE_TAG_RE.search(raw_text)
    if m and m.group(1) in CATEGORIES:
        kategorie = m.group(1)
        raw_text = (raw_text[: m.start()] + raw_text[m.end() :]).strip()

    desc = ""
    m = _DESC_TAG_RE.search(raw_text)
    if m:
        desc = m.group(1)
        raw_text = (raw_text[: m.start()] + raw_text[m.end() :]).strip()

    assignee = DEFAULT_ASSIGNEE
    m = _ASSIGNEE_TAG_RE.search(raw_text)
    if m:
        assignee = next(a for a in ASSIGNEES if a.lower() == m.group(1).lower())
        raw_text = (raw_text[: m.start()] + raw_text[m.end() :]).strip()

    return raw_text, assignee, due, status, kunde, kategorie, desc


def parse_task_line(line: str) -> dict | None:
    """Parst eine Checkbox-Zeile aus context.md. None, wenn keine Aufgaben-Zeile."""
    raw = _strip_checkbox(line)
    if raw is None:
        return None
    done = "- [x]" in line or "- [X]" in line
    text, assignee, due, status, kunde, kategorie, desc = _split_tags(raw)
    return {
        "text": text, "done": done, "assignee": assignee, "due": due, "status": status,
        "kunde": kunde, "kategorie": kategorie, "beschreibung": desc,
    }


def _format_task_line(
    checkbox: str, text: str, assignee: str, due: str | None, status: str = "todo",
    kunde: str | None = None, kategorie: str | None = None, beschreibung: str | None = None,
) -> str:
    line = f"- {checkbox} {text} @{assignee}"
    if due:
        line += f" !due({due})"
    if status != "todo":
        line += f" !status({status})"
    if kunde:
        line += f" !kunde({kunde})"
    if kategorie:
        line += f" !kategorie({kategorie})"
    if beschreibung:
        line += f" !desc[{beschreibung}]"
    return line


def _legacy_urgency_date(text: str) -> datetime | None:
    """Fallback für Alt-Aufgaben ohne !due-Tag, die ein Datum im Freitext haben
    (z.B. "(DEADLINE: 5.7.)")."""
    m = _LEGACY_DATE_RE.search(text)
    if not m:
        return None
    try:
        return datetime(datetime.now().year, int(m.group(2)), int(m.group(1)))
    except Exception:
        return None


def _urgency_from_date(dt: datetime) -> str:
    days_left = (dt - datetime.now()).days
    if days_left <= 7:
        return "urgent"
    if days_left <= 21:
        return "soon"
    return "normal"


def get_tasks() -> list[dict]:
    settings = get_settings()
    try:
        ctx = settings.context_path.read_text(encoding="utf-8")
    except Exception:
        return []

    tasks = []
    for line in ctx.splitlines():
        parsed = parse_task_line(line)
        if parsed is None:
            continue
        if parsed["done"]:
            tasks.append({
                "text": parsed["text"], "urgency": "done", "done": True,
                "assignee": parsed["assignee"], "due": parsed["due"], "status": "done",
                "kunde": parsed["kunde"], "kategorie": parsed["kategorie"], "beschreibung": parsed["beschreibung"],
            })
            continue

        dt = None
        if parsed["due"]:
            try:
                dt = datetime.fromisoformat(parsed["due"])
            except ValueError:
                dt = None
        if dt is None:
            dt = _legacy_urgency_date(parsed["text"])

        tasks.append({
            "text": parsed["text"],
            "urgency": _urgency_from_date(dt) if dt else "normal",
            "assignee": parsed["assignee"],
            "due": parsed["due"],
            "status": parsed["status"],
            "kunde": parsed["kunde"],
            "kategorie": parsed["kategorie"],
            "beschreibung": parsed["beschreibung"],
        })
    return tasks


def _update_task_line(text: str, build_line) -> dict:
    """Sucht die Zeile mit passendem (getaggtem) Aufgabentext und ersetzt sie
    über `build_line(parsed) -> str`."""
    target = text.strip()
    settings = get_settings()
    path = settings.context_path
    lines = path.read_text(encoding="utf-8").splitlines()
    changed = False
    for i, line in enumerate(lines):
        parsed = parse_task_line(line)
        if parsed and parsed["text"] == target:
            lines[i] = build_line(parsed)
            changed = True
            break
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"ok": True, "changed": changed}


def add_task(
    text: str, assignee: str = DEFAULT_ASSIGNEE, due: str | None = None,
    kunde: str | None = None, kategorie: str | None = None, beschreibung: str = "",
) -> dict:
    text = text.strip()
    if not text:
        return {"error": "kein Text"}
    if assignee not in ASSIGNEES:
        return {"error": "ungültige Zuständigkeit"}
    if kategorie and kategorie not in CATEGORIES:
        return {"error": "ungültige Kategorie"}
    if due:
        try:
            datetime.fromisoformat(due)
        except ValueError:
            return {"error": "ungültiges Datum"}
    settings = get_settings()
    path = settings.context_path
    content = path.read_text(encoding="utf-8") if path.exists() else ""
    header = "## Offene Aufgaben"
    entry = _format_task_line("[ ]", text, assignee, due, kunde=kunde, kategorie=kategorie, beschreibung=beschreibung)
    if header in content:
        content = content.replace(header, f"{header}\n{entry}", 1)
    else:
        content = content.rstrip() + f"\n\n{header}\n{entry}\n"
    path.write_text(content, encoding="utf-8")
    return {"ok": True}


def toggle_task(text: str, done: bool) -> dict:
    checkbox = "[x]" if done else "[ ]"
    return _update_task_line(
        text,
        lambda p: _format_task_line(
            checkbox, p["text"], p["assignee"], p["due"], p["status"], p["kunde"], p["kategorie"], p["beschreibung"]
        ),
    )


def set_task_assignee(text: str, assignee: str) -> dict:
    if assignee not in ASSIGNEES:
        return {"error": "ungültige Zuständigkeit"}
    return _update_task_line(
        text,
        lambda p: _format_task_line(
            "[x]" if p["done"] else "[ ]", p["text"], assignee, p["due"], p["status"],
            p["kunde"], p["kategorie"], p["beschreibung"],
        ),
    )


def set_task_due(text: str, due: str | None) -> dict:
    if due:
        try:
            datetime.fromisoformat(due)
        except ValueError:
            return {"error": "ungültiges Datum"}
    return _update_task_line(
        text,
        lambda p: _format_task_line(
            "[x]" if p["done"] else "[ ]", p["text"], p["assignee"], due, p["status"],
            p["kunde"], p["kategorie"], p["beschreibung"],
        ),
    )


def update_task(
    original_text: str, text: str, assignee: str, due: str | None,
    kunde: str | None, kategorie: str | None, beschreibung: str,
) -> dict:
    """Voll-Update aus dem Bearbeiten-Dialog (Umsetzungsplan 2026-07-27) - der
    Titel selbst kann sich ändern, die Zeile wird daher über `original_text`
    gefunden (wie bei den übrigen Settern), aber mit dem neuen Text neu
    geschrieben. done/status bleiben unangetastet (nicht Teil dieses
    Dialogs - siehe toggle_task/set_task_status fürs Kanban-Board)."""
    text = text.strip()
    if not text:
        return {"error": "kein Text"}
    if assignee not in ASSIGNEES:
        return {"error": "ungültige Zuständigkeit"}
    if kategorie and kategorie not in CATEGORIES:
        return {"error": "ungültige Kategorie"}
    if due:
        try:
            datetime.fromisoformat(due)
        except ValueError:
            return {"error": "ungültiges Datum"}
    return _update_task_line(
        original_text,
        lambda p: _format_task_line(
            "[x]" if p["done"] else "[ ]", text, assignee, due, p["status"], kunde, kategorie, beschreibung
        ),
    )


def set_task_status(text: str, status: str) -> dict:
    """Kanban-Spaltenwechsel (Umsetzungsplan 2026-07-27): nur für "todo"/
    "in_progress" gedacht - der Wechsel nach "Erledigt" läuft weiterhin über
    toggle_task (echte Checkbox), daher wird die Checkbox hier bewusst immer
    auf offen gesetzt (ein Kanban-Zug aus der Erledigt-Spalte heraus öffnet
    die Aufgabe wieder, wie in Jira üblich)."""
    if status not in STATUS_VALUES:
        return {"error": "ungültiger Status"}
    return _update_task_line(
        text,
        lambda p: _format_task_line(
            "[ ]", p["text"], p["assignee"], p["due"], status, p["kunde"], p["kategorie"], p["beschreibung"]
        ),
    )


def set_tasks(tasks: list[str]) -> dict:
    """Ersetzt alle offenen (nicht erledigten) Aufgaben durch eine neue Liste.
    Erledigte Aufgaben (- [x]) bleiben unangetastet. Migriert aus
    brain_server.py:_tasks_replace()."""
    settings = get_settings()
    path = settings.context_path
    content = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = content.splitlines()

    kept = [l for l in lines if parse_task_line(l) is None or "- [x]" in l or "- [X]" in l]
    new_lines = [_format_task_line("[ ]", t.strip(), DEFAULT_ASSIGNEE, None) for t in tasks if t.strip()]

    header = "## Offene Aufgaben"
    idx = next((i for i, l in enumerate(kept) if l.strip() == header), -1)
    if idx >= 0:
        kept[idx + 1 : idx + 1] = new_lines
    else:
        kept.append(header)
        kept.extend(new_lines)

    new_content = "\n".join(kept)
    today = datetime.now().strftime("%Y-%m-%d")
    new_content = re.sub(r"^updated: .+$", f"updated: {today}", new_content, flags=re.MULTILINE)
    path.write_text(new_content + "\n", encoding="utf-8")
    return {"ok": True, "count": len(new_lines)}


def delete_task(text: str) -> dict:
    target = text.strip()
    settings = get_settings()
    path = settings.context_path
    lines = path.read_text(encoding="utf-8").splitlines()
    removed = False
    kept = []
    for line in lines:
        parsed = parse_task_line(line)
        if not removed and parsed and parsed["text"] == target:
            removed = True
            continue
        kept.append(line)
    path.write_text("\n".join(kept) + "\n", encoding="utf-8")
    return {"ok": True, "removed": removed}
