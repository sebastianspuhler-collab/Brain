"""Nutzungs-/Kostentracking für Claude-Code-CLI-Anfragen (Umsetzungsplan
2026-07-27). Die CLI liefert am Ende jeder Anfrage ein "result"-Event mit
Token- und Kosten-Angaben (total_cost_usd, usage.{input,output,cache_creation,
cache_read}_tokens) - bisher wurde das nirgends aufgezeichnet, weder im
Hauptchat-Pfad noch beim Entwicklungs-Agenten. Eine JSON-Zeile pro
abgeschlossener Anfrage in _agent/usage_log.jsonl, konsistent mit dem Rest
des Projekts (Markdown/JSON-Dateien im Vault statt einer externen
Datenbank/Zeitreihen-DB)."""
import json
from datetime import datetime, timedelta, timezone

from app.config import get_settings


def log_usage(
    source: str,
    model: str,
    usage: dict | None,
    cost_usd: float | None = None,
    agent_id: str | None = None,
) -> None:
    """Schreibt eine Zeile pro abgeschlossener Anfrage. usage kommt roh aus dem
    CLI-result-Event - fehlende Felder werden defensiv als 0 behandelt, falls
    sich das CLI-Schema mal ändert. Darf einen laufenden Chat nie zum Absturz
    bringen, daher großzügiges try/except."""
    usage = usage or {}
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "model": model,
        "agent_id": agent_id,
        "input_tokens": usage.get("input_tokens") or 0,
        "output_tokens": usage.get("output_tokens") or 0,
        "cache_creation_input_tokens": usage.get("cache_creation_input_tokens") or 0,
        "cache_read_input_tokens": usage.get("cache_read_input_tokens") or 0,
        "cost_usd": cost_usd or 0.0,
    }
    try:
        path = get_settings().usage_log_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _read_entries() -> list[dict]:
    path = get_settings().usage_log_path
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def _tokens(e: dict) -> int:
    return (
        (e.get("input_tokens") or 0)
        + (e.get("output_tokens") or 0)
        + (e.get("cache_creation_input_tokens") or 0)
        + (e.get("cache_read_input_tokens") or 0)
    )


def get_summary(days: int = 14) -> dict:
    """Aggregiert usage_log.jsonl für das Nutzungs-Dashboard: rollierendes
    5-Stunden-Sitzungsfenster und rollierende 7-Tage-Woche (dieselben
    Zeitfenster wie Claudes echte Abo-Limits, siehe Modul-Docstring - echte
    Prozent-Auslastung dieser Limits ist über die CLI nicht abrufbar, nur
    unsere eigene Anfrage-/Token-Zählung im selben Fenster), zusätzlich
    "heute", Aufschlüsselung nach Modell und eine Tagesreihe für die
    letzten `days` Tage (Balken-Chart im Frontend)."""
    entries = _read_entries()
    now = datetime.now(timezone.utc)
    today_key = now.strftime("%Y-%m-%d")
    session_start = now - timedelta(hours=5)
    week_start = now - timedelta(days=7)

    today = {"requests": 0, "tokens": 0, "cost_usd": 0.0}
    session_5h = {"requests": 0, "tokens": 0, "cost_usd": 0.0}
    week = {"requests": 0, "tokens": 0, "cost_usd": 0.0}
    by_model: dict[str, dict] = {}
    by_day: dict[str, dict] = {}

    for e in entries:
        try:
            ts = datetime.fromisoformat(e["ts"])
        except Exception:
            continue
        day_key = ts.strftime("%Y-%m-%d")
        tok = _tokens(e)
        cost = e.get("cost_usd") or 0.0

        if day_key == today_key:
            today["requests"] += 1
            today["tokens"] += tok
            today["cost_usd"] += cost
        if ts >= session_start:
            session_5h["requests"] += 1
            session_5h["tokens"] += tok
            session_5h["cost_usd"] += cost
        if ts >= week_start:
            week["requests"] += 1
            week["tokens"] += tok
            week["cost_usd"] += cost

        m = by_model.setdefault(e.get("model") or "?", {"requests": 0, "tokens": 0, "cost_usd": 0.0})
        m["requests"] += 1
        m["tokens"] += tok
        m["cost_usd"] += cost

        d = by_day.setdefault(day_key, {"tokens": 0, "cost_usd": 0.0})
        d["tokens"] += tok
        d["cost_usd"] += cost

    day_keys = sorted(by_day.keys())[-days:]
    daily = [{"date": d, **by_day[d]} for d in day_keys]

    return {
        "today": today,
        "session_5h": session_5h,
        "week": week,
        "by_model": [
            {"model": m, **v} for m, v in sorted(by_model.items(), key=lambda kv: -kv[1]["cost_usd"])
        ],
        "daily": daily,
    }
