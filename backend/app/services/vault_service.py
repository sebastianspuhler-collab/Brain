"""Vault-Dateioperationen für den Chat-Tool-Use-Loop. Migriert aus
brain_server.py (vault_list, vault_create_folder, vault_move, vault_rename).
Path-Traversal-Guards 1:1 übernommen, da Pfade von der LLM-Tool-Eingabe kommen."""
import shutil
import threading

from app.config import get_settings
from app.services import rag

SKIP_NAMES = {".git", ".obsidian", "__pycache__", ".DS_Store", "node_modules"}


def _within_vault(path) -> bool:
    settings = get_settings()
    return str(path).startswith(str(settings.vault_path.resolve()))


def vault_list(path: str = "") -> str:
    """Listet den Inhalt eines Vault-Ordners auf."""
    settings = get_settings()
    target = (settings.vault_path / path).resolve() if path else settings.vault_path.resolve()
    if not _within_vault(target):
        return "Pfad ausserhalb des Vault"
    if not target.exists():
        return f"Ordner nicht gefunden: {path}"
    lines = [f"Inhalt von: {path or 'Vault-Root'}"]
    try:
        entries = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        for e in entries:
            if e.name in SKIP_NAMES or e.name.startswith("."):
                continue
            marker = "/" if e.is_dir() else f" ({e.stat().st_size} Bytes)"
            lines.append(f"  {'[Ordner] ' if e.is_dir() else '[Datei]  '}{e.name}{'' if e.is_dir() else marker}")
    except PermissionError:
        return "Kein Zugriff"
    return "\n".join(lines)


def vault_create(path: str) -> dict:
    """Erstellt einen neuen Ordner im Vault (auch verschachtelt)."""
    settings = get_settings()
    target = (settings.vault_path / path).resolve()
    if not _within_vault(target):
        return {"ok": False, "error": "Pfad ausserhalb des Vault"}
    try:
        target.mkdir(parents=True, exist_ok=True)
        return {"ok": True, "path": str(target.relative_to(settings.vault_path))}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def vault_move(source: str, destination: str) -> dict:
    """Verschiebt eine Datei oder einen Ordner im Vault."""
    settings = get_settings()
    src_path = (settings.vault_path / source.strip()).resolve()
    dst_path = (settings.vault_path / destination.strip()).resolve()
    if not _within_vault(src_path):
        return {"ok": False, "error": "Quellpfad ausserhalb des Vault"}
    if not _within_vault(dst_path):
        return {"ok": False, "error": "Zielpfad ausserhalb des Vault"}
    if not src_path.exists():
        return {"ok": False, "error": f"Quelle nicht gefunden: {source}"}
    try:
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_path), str(dst_path))
        rel_dst = str(dst_path.relative_to(settings.vault_path))
        threading.Thread(target=rag.reindex_new_files, daemon=True).start()
        return {"ok": True, "from": source, "to": rel_dst}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def vault_rename(path: str, new_name: str) -> dict:
    """Benennt eine Datei oder einen Ordner im Vault um."""
    settings = get_settings()
    old_path = (settings.vault_path / path.strip()).resolve()
    if not _within_vault(old_path):
        return {"ok": False, "error": "Pfad ausserhalb des Vault"}
    if not old_path.exists():
        return {"ok": False, "error": f"Nicht gefunden: {path}"}
    new_path = old_path.parent / new_name.strip()
    try:
        old_path.rename(new_path)
        return {"ok": True, "from": path, "to": str(new_path.relative_to(settings.vault_path))}
    except Exception as e:
        return {"ok": False, "error": str(e)}
