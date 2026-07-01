"""Datei-Browser + Download. Migriert aus brain_server.py (_list_files, _serve_file)."""
import mimetypes

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
