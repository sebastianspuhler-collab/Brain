"""Gesprächsprotokollierung für Kontinuität über Sessions hinweg.
Migriert aus _agent/brain_server.py (log_turn, get_recent_conversations)."""
from datetime import date, datetime, timedelta

from app.config import get_settings


def log_turn(role: str, content: str) -> None:
    settings = get_settings()
    settings.conversations_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    path = settings.conversations_dir / f"{today}.md"
    if not path.exists():
        path.write_text(f"---\ndate: {today}\ntitle: Gespräch {today}\n---\n\n", encoding="utf-8")
    label = "**Sebastian:**" if role == "user" else "**Brain:**"
    ts = datetime.now().strftime("%H:%M")
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n### {ts}\n{label}\n{content.strip()}\n")


def get_recent_conversations() -> str:
    settings = get_settings()
    if not settings.conversations_dir.exists():
        return ""
    today = date.today()
    parts = []
    for delta in (1, 0):
        d = today - timedelta(days=delta)
        log_file = settings.conversations_dir / f"{d.isoformat()}.md"
        if log_file.exists():
            try:
                content = log_file.read_text(encoding="utf-8", errors="ignore")
                if len(content) > 4000:
                    content = "...[frühere Einträge gekürzt]...\n" + content[-4000:]
                parts.append(f"=== GESPRÄCHSLOG {d.strftime('%d.%m.%Y')} ===\n{content}")
            except Exception:
                pass
    return "\n\n".join(parts)
