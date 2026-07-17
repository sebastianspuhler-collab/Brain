"""Eigene benannte Chat-Agenten (Umsetzungsplan-Memo 2026-07-16, Punkt D2).

Ergänzung zum Hauptchat, kein Ersatz: der normale Chat ohne agent_id verhält
sich exakt wie bisher (Standard-System-Prompt aus context.build_system(),
volle Vault-Suche, freie Modellwahl). Ein Agent ist optional wählbar und
bringt zusätzlich: einen Zusatz-Prompt (Persona/Fokus), eine Einschränkung der
RAG-Suche auf bestimmte Vault-Ordner und/oder eine feste Modellwahl. Alle
Agenten liegen gesammelt in einer Datei _agent/agents.json (kleine, selten
bearbeitete Liste - kein eigener Ordner pro Agent nötig)."""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings


def _agents_path() -> Path:
    return get_settings().agent_dir / "agents.json"


def _load_all() -> list[dict]:
    path = _agents_path()
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_all(agents: list[dict]) -> None:
    path = _agents_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(agents, ensure_ascii=False, indent=2), encoding="utf-8")


def list_agents() -> list[dict]:
    return _load_all()


def get_agent(agent_id: str) -> dict | None:
    for a in _load_all():
        if a.get("id") == agent_id:
            return a
    return None


def create_agent(
    name: str,
    system_prompt_zusatz: str = "",
    ordner_filter: list[str] | None = None,
    model: str | None = None,
) -> dict:
    agents = _load_all()
    now = datetime.now(timezone.utc).isoformat()
    agent = {
        "id": str(uuid.uuid4()),
        "name": name.strip() or "Unbenannter Agent",
        "system_prompt_zusatz": system_prompt_zusatz.strip(),
        "ordner_filter": [o.strip() for o in (ordner_filter or []) if o.strip()],
        "model": model or None,
        "created_at": now,
    }
    agents.append(agent)
    _save_all(agents)
    return agent


def update_agent(
    agent_id: str,
    name: str | None = None,
    system_prompt_zusatz: str | None = None,
    ordner_filter: list[str] | None = None,
    model: str | None = None,
) -> dict | None:
    agents = _load_all()
    for a in agents:
        if a.get("id") != agent_id:
            continue
        if name is not None:
            a["name"] = name.strip() or a["name"]
        if system_prompt_zusatz is not None:
            a["system_prompt_zusatz"] = system_prompt_zusatz.strip()
        if ordner_filter is not None:
            a["ordner_filter"] = [o.strip() for o in ordner_filter if o.strip()]
        if model is not None:
            a["model"] = model or None
        _save_all(agents)
        return a
    return None


def delete_agent(agent_id: str) -> bool:
    agents = _load_all()
    remaining = [a for a in agents if a.get("id") != agent_id]
    if len(remaining) == len(agents):
        return False
    _save_all(remaining)
    return True
