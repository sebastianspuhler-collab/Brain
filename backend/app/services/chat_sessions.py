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
                "agent_id": data.get("agent_id"),
            })
        except Exception:
            continue
    sessions.sort(key=lambda s: s["updated_at"], reverse=True)
    return sessions


def list_sessions_for_agent(agent_id: str) -> list[dict]:
    """Chat-Verlauf pro Agent (Umsetzungsplan 2026-07-26): alle Sessions mit
    passender agent_id statt nur der neuesten (vorheriges
    find_session_for_agent) - list_sessions() ist schon nach updated_at
    absteigend sortiert, bleibt hier erhalten. Funktioniert unverändert auch
    für den Entwicklungs-Agenten (reservierte agent_id "dev-agent", kein
    echter Eintrag in agents.json - diese Funktion kennt/braucht das nicht,
    Sessions sind einfach nur mit dem String getaggt)."""
    return [s for s in list_sessions() if s.get("agent_id") == agent_id]


def load_session(session_id: str) -> dict | None:
    path = _session_path(session_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_session(
    session_id: str, messages: list[dict], model: str, agent_id: str | None = None,
    claude_session_id: str | None = None,
) -> dict:
    path = _session_path(session_id)
    now = datetime.now(timezone.utc).isoformat()
    existing = load_session(session_id)
    created_at = existing.get("created_at", now) if existing else now
    # claude_session_id (2026-08-09): die claude-CLI-eigene Session-ID für
    # --resume (siehe claude_cli.py) - None bedeutet hier "unverändert lassen",
    # nicht "löschen", damit die bisherigen Aufrufer (Haupt-Chat im
    # api-Engine-Modus, Zwischenspeichern der reinen Nutzer-Nachricht vor der
    # Antwort, Dev-Agent-Proxy, das PUT-Endpoint unten) die ID nicht jedes Mal
    # kennen/mitschicken müssen, um sie nicht versehentlich zu überschreiben.
    if claude_session_id is None and existing:
        claude_session_id = existing.get("claude_session_id")
    data = {
        "id": session_id,
        "title": _derive_title(messages),
        "model": model,
        "created_at": created_at,
        "updated_at": now,
        "messages": messages,
        "agent_id": agent_id,
        "claude_session_id": claude_session_id,
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
