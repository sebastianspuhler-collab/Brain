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
import time
from datetime import datetime
from pathlib import Path

import combined_leads

STATIC_DIR = Path(__file__).resolve().parent / "static"
EXPORTS_DIR = STATIC_DIR / "exports"
MAX_AGE_SECONDS = 24 * 60 * 60

# (Feldname im get_combined_leads()-Ergebnis, Spaltenüberschrift)
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


def _write_csv(rows: list[dict], path: Path) -> None:
    # utf-8-sig (BOM) statt utf-8, damit Excel Umlaute korrekt anzeigt statt
    # sie ohne BOM als falsch kodiert zu interpretieren.
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([label for _, label in _COLUMNS])
        for r in rows:
            writer.writerow([r.get(key, "") for key, _ in _COLUMNS])


def _write_xlsx(rows: list[dict], path: Path) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = "Leads"
    ws.append([label for _, label in _COLUMNS])
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for r in rows:
        ws.append([r.get(key, "") for key, _ in _COLUMNS])
    for col_cells in ws.columns:
        length = max((len(str(c.value)) for c in col_cells if c.value is not None), default=8)
        ws.column_dimensions[col_cells[0].column_letter].width = min(length + 2, 50)
    wb.save(path)


def export_leads(filter: dict | None = None, format: str = "csv") -> dict:
    fmt = (format or "csv").strip().lower()
    if fmt not in ALLOWED_FORMATS:
        return {"ok": False, "error": f"Unbekanntes Format '{format}' (erlaubt: csv, xlsx)"}

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    _cleanup_old_exports()

    rows = combined_leads.get_combined_leads(filter or {})
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"leads_export_{timestamp}.{fmt}"
    path = EXPORTS_DIR / filename

    if fmt == "csv":
        _write_csv(rows, path)
    else:
        _write_xlsx(rows, path)

    return {
        "ok": True,
        "filename": filename,
        "anzahl_leads": len(rows),
        "download_url": f"/api/lead-agent/exports/{filename}",
    }
