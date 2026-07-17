"""Persistenz für einzelne Chat-Sessions (Umsetzungsplan Memo 2026-07-16, Punkt A2).

Ergänzung zu conversations.py, kein Ersatz: conversations.py loggt Tages-weise für
den System-Prompt der Folgetage (Kontinuität über Tage hinweg), diese Datei hier
speichert einzelne Sessions vollständig wieder-ladbar (Kontinuität über Reloads/
Browser-Neustarts hinweg), damit die Chat-Historie im Frontend nicht mehr verloren
geht. Eine Datei pro Session unter _agent/chat_sessions/{id}.json - bewusst kein
neuer DB-Dienst, konsistent mit dem Rest des Projekts (Markdown/JSON-Dateien im
Vault statt externer Datenbank).
"""
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings


def _sessions_dir() -> Path:
    d = get_settings().agent_dir / "chat_sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _session_path(session_id: str) -> Path:
    # session_id kommt vom Client (crypto.randomUUID()) - trotzdem defensiv gegen
    # Pfad-Traversal absichern, da er direkt in einen Dateinamen einfließt.
    safe_id = re.sub(r"[^a-zA-Z0-9\-]", "", session_id)[:64]
    if not safe_id:
        raise ValueError("Ungültige session_id")
    return _sessions_dir() / f"{safe_id}.json"


def _derive_title(messages: list[dict]) -> str:
    for m in messages:
        if m.get("role") == "user" and m.get("content", "").strip():
            text = m["content"].strip().replace("\n", " ")
            return text[:60] + ("…" if len(text) > 60 else "")
    return "Neuer Chat"


def list_sessions() -> list[dict]:
    sessions = []
    for path in _sessions_dir().glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            sessions.append({
                "id": data.get("id", path.stem),
                "title": data.get("title", "Neuer Chat"),
                "updated_at": data.get("updated_at", ""),
                "model": data.get("model", ""),
            })
        except Exception:
            continue
    sessions.sort(key=lambda s: s["updated_at"], reverse=True)
    return sessions


def load_session(session_id: str) -> dict | None:
    path = _session_path(session_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_session(session_id: str, messages: list[dict], model: str) -> dict:
    path = _session_path(session_id)
    now = datetime.now(timezone.utc).isoformat()
    existing = load_session(session_id)
    created_at = existing.get("created_at", now) if existing else now
    data = {
        "id": session_id,
        "title": _derive_title(messages),
        "model": model,
        "created_at": created_at,
        "updated_at": now,
        "messages": messages,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def delete_session(session_id: str) -> bool:
    path = _session_path(session_id)
    if not path.exists():
        return False
    path.unlink()
    return True


def new_session_id() -> str:
    return str(uuid.uuid4())
