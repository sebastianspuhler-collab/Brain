"""Echter Datei-Export (CSV/XLSX) von get_combined_leads()-Ergebnissen -
Umsetzungsplan Teil C, ersetzt reinen CSV-Text im Chat für "gib mir eine
Liste/Tabelle"-Anfragen.

Ablage in static/exports/ - dieser Ordner wird vom eigenen FastAPI-Prozess
(server.py) NUR intern über /static/exports/<datei> ausgeliefert. Der
lead-agent-Container hat KEINE öffentliche Traefik-Route außer
/lead-agent/webhook (siehe docker-compose.yml) - ein direktes Public-Serving
von Export-Dateien mit Lead-/Kontaktdaten wäre ein offener,
unauthentifizierter Datenabfluss. Öffentlich (authentifiziert) erreichbar ist
der Download deshalb ausschließlich über den bestehenden, Cookie-auth-
gated Backend-Proxy GET /api/lead-agent/exports/{filename}
(backend/app/routers/lead_agent_proxy.py) - exakt dasselbe Auth-Muster wie
/api/lead-agent/ui, keine neue Traefik-Route nötig (bestehender
/api/*-Proxy reicht, siehe dortiger Docstring)."""
import csv
import re
import time
from datetime import datetime
from pathlib import Path

import combined_leads

STATIC_DIR = Path(__file__).resolve().parent / "static"
EXPORTS_DIR = STATIC_DIR / "exports"
MAX_AGE_SECONDS = 24 * 60 * 60

# (Feldname im get_combined_leads()-Ergebnis, Spaltenüberschrift). Reihenfolge
# = Standardspalten, wenn der Aufrufer keine `spalten` angibt.
_COLUMNS = [
    ("firma", "Firma"),
    ("kontakt", "Kontakt"),
    ("quelle", "Quelle"),
    ("status", "Status"),
    ("score", "Score"),
    ("letzter_kontakt", "Letzter Kontakt"),
    ("close_lead_id", "Close-Lead-ID"),
    ("close_link", "Close-Link"),
    ("vault_path", "Vault-Pfad"),
]

# Zusätzlich wählbar über `spalten` (siehe combined_leads._record).
_EXTRA_COLUMNS = [
    ("website", "Website"),
    ("ort", "Ort"),
    ("branche", "Branche"),
    ("mitarbeiter", "Mitarbeiter"),
    ("umsatz", "Umsatz"),
    ("close_status", "Close-Status"),
    ("aehnlich_zu", "Ähnlich zu"),
    ("quellen", "Quellen"),
    ("angelegt", "Angelegt am"),
]
_LABELS = dict(_COLUMNS + _EXTRA_COLUMNS)


def resolve_columns(spalten: str | list[str] | None) -> list[tuple[str, str]]:
    """'firma, website, ort' (oder Liste) -> [(key, label)]. Unbekannte Keys
    werden abgelehnt (ValueError) statt leere Spalten zu erzeugen."""
    if not spalten:
        return list(_COLUMNS)
    keys = [k.strip() for k in (spalten.split(",") if isinstance(spalten, str) else spalten) if str(k).strip()]
    unknown = [k for k in keys if k not in _LABELS]
    if unknown:
        raise ValueError(f"Unbekannte Spalte(n): {', '.join(unknown)}. Verfügbar: {', '.join(_LABELS)}")
    return [(k, _LABELS[k]) for k in keys]


ALLOWED_FORMATS = {"csv", "xlsx"}


def _cleanup_old_exports() -> None:
    """Einfaches Aufräumen ohne Cron (Umsetzungsplan Teil C): läuft bei jedem
    export_leads()-Aufruf, löscht eigene Export-Dateien >24h. Kein Cleanup
    fremder Dateien im Ordner - nur das eigene leads_export_*-Namensmuster."""
    if not EXPORTS_DIR.exists():
        return
    cutoff = time.time() - MAX_AGE_SECONDS
    for p in EXPORTS_DIR.glob("leads_export_*"):
        try:
            if p.is_file() and p.stat().st_mtime < cutoff:
                p.unlink()
        except OSError:
            pass


def _write_csv(rows: list[dict], path: Path, columns: list[tuple[str, str]]) -> None:
    # utf-8-sig (BOM) statt utf-8, damit Excel Umlaute korrekt anzeigt statt
    # sie ohne BOM als falsch kodiert zu interpretieren.
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([label for _, label in columns])
        for r in rows:
            writer.writerow([r.get(key, "") for key, _ in columns])


def _write_xlsx(rows: list[dict], path: Path, columns: list[tuple[str, str]]) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = "Leads"
    ws.append([label for _, label in columns])
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for r in rows:
        ws.append([r.get(key, "") for key, _ in columns])
    for col_cells in ws.columns:
        length = max((len(str(c.value)) for c in col_cells if c.value is not None), default=8)
        ws.column_dimensions[col_cells[0].column_letter].width = min(length + 2, 50)
    wb.save(path)


def _write_file(rows: list[dict], columns: list[tuple[str, str]], fmt: str, prefix: str) -> dict:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    _cleanup_old_exports()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{prefix}_{timestamp}.{fmt}"
    path = EXPORTS_DIR / filename
    if fmt == "csv":
        _write_csv(rows, path, columns)
    else:
        _write_xlsx(rows, path, columns)
    return {
        "ok": True,
        "filename": filename,
        "anzahl_zeilen": len(rows),
        "spalten": [label for _, label in columns],
        "download_url": f"/api/lead-agent/exports/{filename}",
    }


def export_leads(filter: dict | None = None, format: str = "csv", spalten: str | list[str] | None = None) -> dict:
    fmt = (format or "csv").strip().lower()
    if fmt not in ALLOWED_FORMATS:
        return {"ok": False, "error": f"Unbekanntes Format '{format}' (erlaubt: csv, xlsx)"}
    try:
        columns = resolve_columns(spalten)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    rows, meta = combined_leads.get_combined_leads_with_meta(filter or {})
    result = _write_file(rows, columns, fmt, "leads_export")
    result["anzahl_leads"] = len(rows)
    if not meta["close_verfuegbar"]:
        result["warnung"] = f"Close war nicht erreichbar - Export enthält nur Vault-Leads ({meta['close_fehler']})"
    return result


def export_table(rows: list[dict], spalten: list[str] | None = None, format: str = "xlsx", dateiname: str = "tabelle") -> dict:
    """Exportiert eine BELIEBIGE, vom Agenten zusammengestellte Tabelle (z.B.
    Rechercheergebnisse, Abgleichslisten) - nicht nur Vault/Close-Bestand.
    spalten: Reihenfolge/Auswahl der Schlüssel; leer = alle Schlüssel in der
    Reihenfolge ihres ersten Auftretens. Spaltenüberschrift = Schlüssel."""
    fmt = (format or "xlsx").strip().lower()
    if fmt not in ALLOWED_FORMATS:
        return {"ok": False, "error": f"Unbekanntes Format '{format}' (erlaubt: csv, xlsx)"}
    rows = [r for r in (rows or []) if isinstance(r, dict)]
    if not rows:
        return {"ok": False, "error": "Keine Zeilen übergeben."}
    keys = list(spalten) if spalten else list(dict.fromkeys(k for r in rows for k in r))
    columns = [(k, k) for k in keys]
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", dateiname or "tabelle").strip("_")[:40] or "tabelle"
    flat = [{k: (", ".join(map(str, v)) if isinstance(v, (list, tuple)) else "" if v is None else v) for k, v in r.items()} for r in rows]
    return _write_file(flat, columns, fmt, f"leads_export_{safe}")
