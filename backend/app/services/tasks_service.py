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


def _strip_checkbox(line: str) -> str | None:
    """Gibt den Aufgabentext (inkl. Tags) ohne Checkbox-Präfix zurück, oder None."""
    if "- [ ]" in line:
        return line.replace("- [ ]", "").strip()
    if "- [x]" in line or "- [X]" in line:
        return line.replace("- [x]", "").replace("- [X]", "").strip()
    return None


def _split_tags(raw_text: str) -> tuple[str, str, str | None]:
    """Trennt @Zuständig- und !due(...)-Tags vom Aufgabentext."""
    due = None
    m = _DUE_TAG_RE.search(raw_text)
    if m:
        due = m.group(1)
        raw_text = (raw_text[: m.start()] + raw_text[m.end() :]).strip()

    assignee = DEFAULT_ASSIGNEE
    m = _ASSIGNEE_TAG_RE.search(raw_text)
    if m:
        assignee = next(a for a in ASSIGNEES if a.lower() == m.group(1).lower())
        raw_text = (raw_text[: m.start()] + raw_text[m.end() :]).strip()

    return raw_text, assignee, due


def parse_task_line(line: str) -> dict | None:
    """Parst eine Checkbox-Zeile aus context.md. None, wenn keine Aufgaben-Zeile."""
    raw = _strip_checkbox(line)
    if raw is None:
        return None
    done = "- [x]" in line or "- [X]" in line
    text, assignee, due = _split_tags(raw)
    return {"text": text, "done": done, "assignee": assignee, "due": due}


def _format_task_line(checkbox: str, text: str, assignee: str, due: str | None) -> str:
    line = f"- {checkbox} {text} @{assignee}"
    if due:
        line += f" !due({due})"
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
                "assignee": parsed["assignee"], "due": parsed["due"],
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


def add_task(text: str, assignee: str = DEFAULT_ASSIGNEE, due: str | None = None) -> dict:
    text = text.strip()
    if not text:
        return {"error": "kein Text"}
    if assignee not in ASSIGNEES:
        return {"error": "ungültige Zuständigkeit"}
    if due:
        try:
            datetime.fromisoformat(due)
        except ValueError:
            return {"error": "ungültiges Datum"}
    settings = get_settings()
    path = settings.context_path
    content = path.read_text(encoding="utf-8") if path.exists() else ""
    header = "## Offene Aufgaben"
    entry = _format_task_line("[ ]", text, assignee, due)
    if header in content:
        content = content.replace(header, f"{header}\n{entry}", 1)
    else:
        content = content.rstrip() + f"\n\n{header}\n{entry}\n"
    path.write_text(content, encoding="utf-8")
    return {"ok": True}


def toggle_task(text: str, done: bool) -> dict:
    checkbox = "[x]" if done else "[ ]"
    return _update_task_line(
        text, lambda p: _format_task_line(checkbox, p["text"], p["assignee"], p["due"])
    )


def set_task_assignee(text: str, assignee: str) -> dict:
    if assignee not in ASSIGNEES:
        return {"error": "ungültige Zuständigkeit"}
    return _update_task_line(
        text,
        lambda p: _format_task_line("[x]" if p["done"] else "[ ]", p["text"], assignee, p["due"]),
    )


def set_task_due(text: str, due: str | None) -> dict:
    if due:
        try:
            datetime.fromisoformat(due)
        except ValueError:
            return {"error": "ungültiges Datum"}
    return _update_task_line(
        text,
        lambda p: _format_task_line("[x]" if p["done"] else "[ ]", p["text"], p["assignee"], due),
    )


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
