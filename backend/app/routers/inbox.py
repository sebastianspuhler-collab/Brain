"""Inbox-Verarbeitung, Datei-Upload, manuelles Merken. Migriert aus brain_server.py
(_handle_upload, api_remember, /api/inbox_process). FastAPIs UploadFile ersetzt das
manuelle Multipart-Parsing aus dem Original."""
import base64
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile
from pydantic import BaseModel

from app.config import get_settings
from app.deps import get_current_user
from app.services import classify, memory, rag
from app.services.anthropic_client import get_client

router = APIRouter(prefix="/api", tags=["inbox"])

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


class RememberRequest(BaseModel):
    text: str


def _run_inbox_and_reindex() -> dict:
    result = classify.run_inbox()
    new_files = rag.reindex_new_files()
    for rel, content in new_files:
        memory.learn_from_file(rel, content)
    result["new_indexed"] = len(new_files)
    return result


@router.post("/inbox_process")
def inbox_process(user: str = Depends(get_current_user)):
    return _run_inbox_and_reindex()


@router.post("/remember")
def remember(body: RememberRequest, user: str = Depends(get_current_user)):
    if not body.text.strip():
        return {"error": "kein Text"}
    memory.append_to_memory("KONTEXT", body.text)
    return {"ok": True}


@router.post("/upload")
async def upload(file: UploadFile, user: str = Depends(get_current_user)):
    settings = get_settings()
    settings.inbox_dir.mkdir(parents=True, exist_ok=True)

    filename = Path(file.filename).name
    body = await file.read()
    inbox_path = settings.inbox_dir / filename
    inbox_path.write_bytes(body)

    suffix = Path(filename).suffix.lower()
    if suffix in IMAGE_EXTS:
        try:
            b64 = base64.standard_b64encode(body).decode()
            mt = "image/jpeg" if suffix in (".jpg", ".jpeg") else "image/png"
            vision_result = get_client().messages.create(
                model="claude-sonnet-4-6", max_tokens=2000,
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": mt, "data": b64}},
                    {"type": "text", "text": "Extrahiere ALLEN Text und ALLE Zahlen/Daten aus diesem Bild. Formatiere als sauberen Markdown-Text. Nichts weglassen."},
                ]}],
            )
            transcription = vision_result.content[0].text
            md_path = settings.inbox_dir / (Path(filename).stem + "_vision.md")
            md_path.write_text(f"# {Path(filename).stem}\n\n{transcription}", encoding="utf-8")
            inbox_path.unlink(missing_ok=True)
        except Exception:
            pass  # Original weiterverarbeiten, falls Vision fehlschlägt

    result = _run_inbox_and_reindex()
    result["filename"] = filename
    return result
