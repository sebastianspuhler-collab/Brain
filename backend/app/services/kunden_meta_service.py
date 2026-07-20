"""Manuell gepflegte Zusatzdaten pro Kunde/Interessent fürs Dashboard
(Sebastian, 2026-07-18, Status-Pipeline statt Ampel seit 2026-07-19):
Archivieren (ausblenden, ohne Vault-Dateien anzutasten), Notiz-Text und eine
Status-Übersteuerung für Fälle, in denen der automatisch abgeleitete
Pipeline-Status nicht zur Realität passt (v.a. "fulfillment"/"abgeschlossen" -
das lässt sich aus Ordnerinhalten allein nicht verlässlich erkennen, siehe
dashboard.py:_status_automatisch). Liegt bewusst als eigene JSON-Datei in
_agent/, nicht als Datei im Kundenordner selbst - Metadaten fürs UI, kein
Vault-Inhalt. Gilt einheitlich für Kunden/-Ordner UND Leads/-Einträge (Key ist
einfach der Anzeigename, unabhängig von der Herkunft).

Selbes Muster wie agents_service.py: komplette Datei bei jedem Schreibvorgang
neu geschrieben, kein Lock - unkritisch bei seltenen UI-Edits."""
import json
from pathlib import Path

from app.config import get_settings

_DEFAULT = {"archiviert": False, "status_override": None, "notiz": "", "overrides": {}}


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
    # "overrides" per dict.get statt direktem Zugriff, damit vor dieser
    # Erweiterung gespeicherte Einträge (ohne das Feld) nicht crashen.
    eintrag = {**_DEFAULT, **_load_all().get(kunde, {})}
    eintrag["overrides"] = eintrag.get("overrides") or {}
    return eintrag


def upsert_meta(
    kunde: str,
    archiviert: bool | None = None,
    status_override: str | None = None,
    notiz: str | None = None,
    overrides: dict[str, str] | None = None,
) -> dict:
    data = _load_all()
    eintrag = {**_DEFAULT, **data.get(kunde, {})}
    eintrag["overrides"] = eintrag.get("overrides") or {}
    if archiviert is not None:
        eintrag["archiviert"] = archiviert
    if status_override is not None:
        eintrag["status_override"] = status_override or None
    if notiz is not None:
        eintrag["notiz"] = notiz
    if overrides is not None:
        # Merge statt Ersetzen, damit z.B. nur "anzeige_name" gesetzt werden
        # kann, ohne einen bereits gesetzten "aktueller_stand"-Override zu
        # verlieren. Leerer String löscht das einzelne Override-Feld wieder.
        for feld, wert in overrides.items():
            if wert:
                eintrag["overrides"][feld] = wert
            else:
                eintrag["overrides"].pop(feld, None)
    data[kunde] = eintrag
    _save_all(data)
    return eintrag
