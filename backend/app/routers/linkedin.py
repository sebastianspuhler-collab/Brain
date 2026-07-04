"""LinkedIn-Autoposter-Bridge-Endpoints. Migriert aus brain_server.py (api_linkedin_*)."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.deps import get_current_user
from app.services import linkedin_service

router = APIRouter(prefix="/api/linkedin", tags=["linkedin"])


class DirectionRequest(BaseModel):
    prompt: str


class GenerateIdeasRequest(BaseModel):
    focus: str = ""


class GeneratePostsRequest(BaseModel):
    spec: str = ""


class PushBufferRequest(BaseModel):
    text: str
    scheduled_at: str | None = None  # ISO-8601, z.B. "2026-07-08T09:30:00+02:00"


@router.get("/ideas")
def ideas(user: str = Depends(get_current_user)):
    return linkedin_service.get_ideas()


@router.get("/posts")
def posts(user: str = Depends(get_current_user)):
    return linkedin_service.get_posts()


@router.get("/direction")
def get_direction(user: str = Depends(get_current_user)):
    return linkedin_service.get_direction()


@router.post("/direction")
def set_direction(body: DirectionRequest, user: str = Depends(get_current_user)):
    return linkedin_service.set_direction(body.prompt)


@router.post("/generate-ideas")
def generate_ideas(body: GenerateIdeasRequest, user: str = Depends(get_current_user)):
    return linkedin_service.generate_ideas(body.focus)


@router.post("/generate-posts")
def generate_posts(body: GeneratePostsRequest, user: str = Depends(get_current_user)):
    return linkedin_service.generate_posts(body.spec)


@router.post("/push-buffer")
def push_buffer(body: PushBufferRequest, user: str = Depends(get_current_user)):
    return linkedin_service.buffer_push(body.text, body.scheduled_at)
