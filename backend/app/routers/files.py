"""Datei-Browser + Download. Migriert aus brain_server.py (_list_files, _serve_file)."""
import io
import mimetypes
import re
from pathlib import Path

import markdown as md
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from xhtml2pdf import pisa

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


def _build_tree_node(dir_path: Path, rel_parts: tuple) -> dict:
    children = []
    try:
        entries = sorted(dir_path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except PermissionError:
        entries = []
    for e in entries:
        if e.name in _SKIP or e.name.startswith("."):
            continue
        if e.is_dir():
            children.append(_build_tree_node(e, rel_parts + (e.name,)))
        else:
            if e.suffix.lower() in _SKIP_EXT:
                continue
            rel = "/".join(rel_parts + (e.name,))
            children.append({
                "name": e.name,
                "path": rel,
                "type": "file",
                "size": e.stat().st_size,
                "url": f"/api/files/download/{rel}",
            })
    return {
        "name": dir_path.name,
        "path": "/".join(rel_parts),
        "type": "folder",
        "children": children,
    }


@router.get("/files/tree")
def files_tree(user: str = Depends(get_current_user)):
    """Ordnerbaum-Ansicht des Vaults (Kunden/Finanzen/Leads/... verschachtelt,
    wie auf dem Mac), Ergänzung zur bisherigen flachen Liste oben."""
    settings = get_settings()
    return _build_tree_node(settings.vault_path, ())


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


# ── Transkript-Download als PDF (Sebastian, 2026-07-28) ─────────────────────
# Meeting-Notizen sind im Vault als .md abgelegt (siehe classify.py::process_file),
# der Download-Button in der Transkripte-Übersicht (MeetingsPage.tsx) soll aber
# ein lesbares PDF liefern statt der rohen Markdown-Datei. Rein clientseitig
# beim Download gerendert (kein zusätzliches .pdf im Vault) - dieselbe .md
# bleibt weiter die Quelle der Wahrheit.
_PDF_CSS = """
@page { margin: 2cm; }
body { font-family: "DejaVu Sans", sans-serif; font-size: 10.5pt; line-height: 1.45; }
h1 { font-size: 16pt; margin-bottom: 4pt; }
h2 { font-size: 13pt; margin-top: 14pt; border-bottom: 1px solid #ccc; padding-bottom: 2pt; }
table { border-collapse: collapse; width: 100%; margin: 8pt 0; }
th, td { border: 1px solid #ccc; padding: 4pt 6pt; text-align: left; font-size: 9.5pt; }
code { font-family: "DejaVu Sans Mono", monospace; background: #f2f2f2; }
"""


def _markdown_to_pdf(text: str) -> bytes:
    html = md.markdown(text, extensions=["extra", "sane_lists"])
    full_html = f"<html><head><style>{_PDF_CSS}</style></head><body>{html}</body></html>"
    buffer = io.BytesIO()
    pisa.CreatePDF(src=full_html, dest=buffer, encoding="utf-8")
    return buffer.getvalue()


@router.get("/files/download-pdf/{rel_path:path}")
def download_file_as_pdf(rel_path: str, user: str = Depends(get_current_user)):
    settings = get_settings()
    target = (settings.vault_path / rel_path).resolve()
    if not str(target).startswith(str(settings.vault_path.resolve())):
        raise HTTPException(status_code=403, detail="forbidden")
    if not target.exists() or not target.is_file() or target.suffix.lower() != ".md":
        raise HTTPException(status_code=404, detail="not found")
    text = target.read_text(encoding="utf-8", errors="ignore")
    pdf_bytes = _markdown_to_pdf(text)
    filename = target.stem + ".pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
