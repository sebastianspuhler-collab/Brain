"""Zugriff auf Kunden/<Firma>/ - etablierte Kundenbeziehungen mit
TATSÄCHLICHEM Kontakt (siehe CLAUDE.md: "ein Lead mit mehr als einem
Dokument bekommt sofort einen eigenen Kunden/[Firma]/-Ordner"). Bisher waren
diese Ordner für den Lead-Agenten komplett unsichtbar - vault_leads.py liest
ausschließlich Leads/*.md. Grund für den Abgleich (Umsetzungsplan
2026-09-06, "F-Tronic steht in beiden drin"): F-Tronic existiert als voller
Kunden/F-Tronic/-Ordner UND als eigener Close-Lead, aber get_combined_leads()
hat das nie erkannt, weil Kunden/-Ordner schlicht nie gelesen wurden.

Kunden/-Ordner haben KEINE einzelne Profil-/Frontmatter-Datei wie
Leads/*.md, nur Unterordner mit Einzeldokumenten (Dokumente/, Meetings/,
Angebote/, Vertraege/, jeweils mit MD/-Unterordner) - deshalb hier kein
Frontmatter-Parser, nur Ordnername (=Firma) + eine eigene, schlanke
close_lead_id.txt pro Ordner für die Close-Verknüpfung. Bewusst NICHT in
kunden_status_cache.json abgelegt: dieser Cache wird vom Backend
(kunden_status_service.py) automatisch neu berechnet/überschrieben und ist
kein stabiler Ablageort für eine vom Lead-Agenten gepflegte Referenz."""
from pathlib import Path

from config import get_settings

_EXCLUDED = {"_Vorlage"}
_LINK_FILENAME = "close_lead_id.txt"


def kunden_dir() -> Path:
    return get_settings().vault_path / "Kunden"


def read_close_lead_id(kunde_path: Path) -> str:
    link = kunde_path / _LINK_FILENAME
    if not link.exists():
        return ""
    return link.read_text(encoding="utf-8", errors="ignore").strip()


def link_to_close(kunde_path: Path, close_lead_id: str) -> None:
    (kunde_path / _LINK_FILENAME).write_text(close_lead_id.strip() + "\n", encoding="utf-8")


def list_kunden() -> list[dict]:
    """Alle etablierten Kundenordner (Firma = Ordnername), inkl. bereits
    bekannter close_lead_id (leer, falls noch nicht verknüpft)."""
    d = kunden_dir()
    if not d.exists():
        return []
    result = []
    for p in sorted(d.iterdir()):
        if not p.is_dir() or p.name in _EXCLUDED or p.name.startswith("."):
            continue
        result.append({"firma": p.name, "path": str(p), "close_lead_id": read_close_lead_id(p)})
    return result


def find_kunde(name_or_path: str) -> dict | None:
    """Analog zu vault_leads.find_lead: exakter Pfad zuerst (muss direkt
    unter Kunden/ liegen), sonst Stichwortsuche im Ordnernamen."""
    settings = get_settings()
    direct = settings.vault_path / name_or_path
    if direct.is_dir() and direct.parent == kunden_dir() and direct.name not in _EXCLUDED:
        return {"firma": direct.name, "path": str(direct), "close_lead_id": read_close_lead_id(direct)}

    needle = name_or_path.lower().strip()
    for k in list_kunden():
        if needle in k["firma"].lower():
            return k
    return None
