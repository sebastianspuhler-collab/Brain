"""Manuell gepflegte Zusatzdaten pro Kunde fürs Dashboard (Sebastian, 2026-07-18):
Archivieren (ausblenden, ohne Vault-Dateien anzutasten), Notiz-Text und eine
Ampel-Übersteuerung für Fälle, in denen die automatisch berechnete Ampel nicht
zur Realität passt. Liegt bewusst als eigene JSON-Datei in _agent/, nicht als
Datei im Kundenordner selbst - Metadaten fürs UI, kein Vault-Inhalt.

Selbes Muster wie agents_service.py: komplette Datei bei jedem Schreibvorgang
neu geschrieben, kein Lock - unkritisch bei seltenen UI-Edits."""
import json
from pathlib import Path

from app.config import get_settings


def _kunden_meta_path() -> Path:
    return get_settings().agent_dir / "kunden_meta.json"


def _load_all() -> dict:
    path = _kunden_meta_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_all(data: dict) -> None:
    path = _kunden_meta_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_meta(kunde: str) -> dict:
    return _load_all().get(kunde, {"archiviert": False, "ampel_override": None, "notiz": ""})


def upsert_meta(
    kunde: str,
    archiviert: bool | None = None,
    ampel_override: str | None = None,
    notiz: str | None = None,
) -> dict:
    data = _load_all()
    eintrag = data.get(kunde, {"archiviert": False, "ampel_override": None, "notiz": ""})
    if archiviert is not None:
        eintrag["archiviert"] = archiviert
    if ampel_override is not None:
        eintrag["ampel_override"] = ampel_override or None
    if notiz is not None:
        eintrag["notiz"] = notiz
    data[kunde] = eintrag
    _save_all(data)
    return eintrag
