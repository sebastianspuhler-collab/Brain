"""YouTube-Buffer-Bridge-Endpoints. Analog zu routers/linkedin.py."""
import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import get_settings
from app.deps import get_current_user
from app.services import youtube_service

router = APIRouter(prefix="/api/youtube", tags=["youtube"])


class GenerateMetadataRequest(BaseModel):
    filename: str
    topic: str


class UpdateMetadataRequest(BaseModel):
    filename: str
    title: str | None = None
    description: str | None = None
    category_id: str | None = None
    privacy: str | None = None
    topic: str | None = None


class PushBufferRequest(BaseModel):
    filename: str
    scheduled_at: str | None = None


@router.get("/videos")
def videos(user: str = Depends(get_current_user)):
    return youtube_service.list_videos()


@router.post("/upload")
async def upload(file: UploadFile, user: str = Depends(get_current_user)):
    body = await file.read()
    result = youtube_service.save_upload(file.filename or "video.mp4", body)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/generate-metadata")
def generate_metadata(body: GenerateMetadataRequest, user: str = Depends(get_current_user)):
    return youtube_service.generate_metadata(body.filename, body.topic)


@router.post("/metadata")
def update_metadata(body: UpdateMetadataRequest, user: str = Depends(get_current_user)):
    return youtube_service.update_metadata(
        body.filename, title=body.title, description=body.description,
        category_id=body.category_id, privacy=body.privacy, topic=body.topic,
    )


@router.post("/push-buffer")
def push_buffer(body: PushBufferRequest, user: str = Depends(get_current_user)):
    return youtube_service.push_to_buffer(body.filename, body.scheduled_at)


@router.delete("/videos/{filename}")
def delete_video(filename: str, user: str = Depends(get_current_user)):
    result = youtube_service.delete_video(filename)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/media/{filename}")
def media(filename: str):
    # Bewusst OHNE get_current_user - Buffers Server muss diese URL ohne
    # Session-Cookie abrufen können, um das Video hochzuladen. Schutz kommt
    # stattdessen über den unratbaren Token im Dateinamen (siehe save_upload).
    safe_name = Path(filename).name
    target = get_settings().youtube_media_dir / safe_name
    if not target.exists() or not target.is_file() or target.suffix.lower() not in youtube_service.VIDEO_EXTS:
        raise HTTPException(status_code=404, detail="not found")
    mime = mimetypes.guess_type(str(target))[0] or "video/mp4"
    return FileResponse(target, media_type=mime, filename=target.name)
