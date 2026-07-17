"""Datei-Browser + Download. Migriert aus brain_server.py (_list_files, _serve_file)."""
import mimetypes
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.config import get_settings
from app.deps import get_current_user

router = APIRouter(prefix="/api", tags=["files"])

_SKIP = {
    "_inbox", ".git", ".obsidian", "_fehler", "__pycache__", "_agent",
    "node_modules", ".claude", ".venv",
    # App-Code lebt im selben Repo wie der Vault - im Datei-Browser des
    # Dashboards soll aber nur Vault-Inhalt (Kunden, Finanzen, ...) auftauchen.
    "backend", "frontend", "docker-compose.yml", "README.md", "DEPLOY.md",
}
_SKIP_EXT = {".pyc", ".log", ".pid", ".bin"}


@router.get("/files")
def list_files(user: str = Depends(get_current_user)):
    settings = get_settings()
    files = []
    for f in sorted(settings.vault_path.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(settings.vault_path)
        parts = rel.parts
        if any(p in _SKIP or p.startswith(".") for p in parts):
            continue
        if f.suffix.lower() in _SKIP_EXT:
            continue
        files.append({
            "path": str(rel).replace("\\", "/"),
            "name": f.name,
            "size": f.stat().st_size,
            "url": "/api/files/download/" + str(rel).replace("\\", "/"),
        })
    return {"files": files}


def _parse_meeting_meta(path: Path) -> dict:
    """Liest Datum aus dem Frontmatter und den Anfang der Zusammenfassung aus
    einer Meeting-.md-Datei - keine Klassifizierung, nur einfaches Parsen von
    Feldern, die process_file() ohnehin schon in jede Notiz schreibt."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return {}
    meta: dict = {}
    fm_match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if fm_match:
        for line in fm_match.group(1).splitlines():
            if line.strip().startswith("datum:"):
                meta["datum"] = line.split(":", 1)[1].strip()
    summary_match = re.search(r"## Zusammenfassung\n(.+?)(\n##|\Z)", text, re.DOTALL)
    if summary_match:
        meta["zusammenfassung"] = summary_match.group(1).strip()[:300]
    return meta


@router.get("/meetings")
def list_meetings(user: str = Depends(get_current_user)):
    """Meeting Cockpit (Umsetzungsplan-Memo 2026-07-16, Punkt B2): vault-weite
    Übersicht aller Meeting-Notizen statt nur verteilt in Kunden/[Firma]/Meetings/
    einsehbar. Reine Ergänzung - keine neue Klassifizierungslogik, nutzt nur die
    Ordnerkonvention aus classify.py und die von process_file() bereits
    geschriebenen Frontmatter-/Zusammenfassungs-Felder."""
    settings = get_settings()
    meetings = []
    for f in sorted(settings.vault_path.rglob("*.md")):
        rel = f.relative_to(settings.vault_path)
        parts = rel.parts
        if "Meetings" not in parts:
            continue
        if any(p in _SKIP or p.startswith(".") for p in parts):
            continue
        meta = _parse_meeting_meta(f)
        kunde = parts[1] if parts[0] == "Kunden" and len(parts) > 1 else None
        meetings.append({
            "path": str(rel).replace("\\", "/"),
            "name": f.stem,
            "kunde": kunde,
            "datum": meta.get("datum", ""),
            "zusammenfassung": meta.get("zusammenfassung", ""),
            "url": "/api/files/download/" + str(rel).replace("\\", "/"),
        })
    meetings.sort(key=lambda m: m["datum"], reverse=True)
    return {"meetings": meetings}


_STANDARD_ORDNER = ("Vertraege", "Angebote", "Meetings", "Dokumente")


@router.get("/spaces")
def list_spaces(user: str = Depends(get_current_user)):
    """Spaces mit Vollständigkeits-Score (Umsetzungsplan-Memo 2026-07-16, Punkt
    D3): pro Kunde, welche der vier Standard-Unterordner (dieselben, die
    classify.classify() für jeden neuen Kunden automatisch anlegt) tatsächlich
    Dateien enthalten. Bewusst rein faktenbasiert (Dateianzahl pro Ordner) statt
    einer KI-Einschätzung "was fehlt" - eine LLM-Vermutung wäre hier nicht durch
    echte Daten gedeckt und würde gegen die Projektregel verstoßen, niemals
    Zahlen/Einschätzungen zu erfinden, wo echte Daten fehlen."""
    settings = get_settings()
    kunden_dir = settings.vault_path / "Kunden"
    if not kunden_dir.exists():
        return {"spaces": []}

    result = []
    for kunde_path in sorted(kunden_dir.iterdir()):
        # ".": versteckte Ordner; "[": Platzhalter-/Vorlagenordner wie das
        # gefundene "[NeuerKunde]"; "_": Vorlagenordner wie das gefundene
        # "_Vorlage" (passend zur Vault-Konvention, dass "_"-Ordner intern/
        # kein Kunde sind, siehe _agent/_inbox auf oberster Ebene)
        if not kunde_path.is_dir() or kunde_path.name.startswith((".", "[", "_")):
            continue
        ordner_status = {}
        for sub in _STANDARD_ORDNER:
            sub_path = kunde_path / sub
            ordner_status[sub] = len([f for f in sub_path.glob("*") if f.is_file()]) if sub_path.exists() else 0

        vorhanden = sum(1 for c in ordner_status.values() if c > 0)
        fehlend = [o for o, c in ordner_status.items() if c == 0]
        result.append({
            "kunde": kunde_path.name,
            "score": round(vorhanden / len(_STANDARD_ORDNER) * 100),
            "ordner": ordner_status,
            "fehlend": fehlend,
        })

    result.sort(key=lambda s: s["score"])
    return {"spaces": result}


@router.get("/files/download/{rel_path:path}")
def download_file(rel_path: str, user: str = Depends(get_current_user)):
    settings = get_settings()
    target = (settings.vault_path / rel_path).resolve()
    # Path-Traversal-Schutz: aufgelöster Pfad muss innerhalb des Vaults bleiben
    if not str(target).startswith(str(settings.vault_path.resolve())):
        raise HTTPException(status_code=403, detail="forbidden")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="not found")
    mime = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
    return FileResponse(target, media_type=mime, filename=target.name)
