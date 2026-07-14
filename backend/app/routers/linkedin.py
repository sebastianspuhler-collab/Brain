"""LinkedIn-Autoposter-Bridge-Endpoints. Migriert aus brain_server.py (api_linkedin_*)."""
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.deps import get_current_user
from app.services import linkedin_service

router = APIRouter(prefix="/api/linkedin", tags=["linkedin"])


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


class DirectionRequest(BaseModel):
    prompt: str


class GenerateIdeasRequest(BaseModel):
    focus: str = ""


class GeneratePostsRequest(BaseModel):
    spec: str = ""


class PushBufferRequest(BaseModel):
    text: str
    scheduled_at: str | None = None  # ISO-8601, z.B. "2026-07-08T09:30:00+02:00"


class PostChatMessage(BaseModel):
    role: str
    content: str


class PostChatRequest(BaseModel):
    messages: list[PostChatMessage]


class UpdatePostRequest(BaseModel):
    text: str


@router.get("/ideas")
def ideas(user: str = Depends(get_current_user)):
    return linkedin_service.get_ideas()


@router.get("/posts")
def posts(user: str = Depends(get_current_user)):
    return linkedin_service.get_posts()


@router.get("/posts/{post_id}")
def post_detail(post_id: str, user: str = Depends(get_current_user)):
    post = linkedin_service.get_post(post_id)
    if not post:
        return {"error": f"Post {post_id} nicht gefunden"}
    return post


@router.post("/posts/{post_id}")
def update_post(post_id: str, body: UpdatePostRequest, user: str = Depends(get_current_user)):
    return linkedin_service.update_post_text(post_id, body.text)


@router.post("/posts/{post_id}/chat")
def post_chat(post_id: str, body: PostChatRequest, user: str = Depends(get_current_user)):
    def stream():
        messages = [m.model_dump() for m in body.messages]
        result = linkedin_service.chat_about_post(post_id, messages)
        if result.get("error"):
            yield _sse({"error": result["error"]})
        else:
            yield _sse({"chunk": result.get("antwort", "")})
            if result.get("changed"):
                yield _sse({"post_updated": True, "text": result.get("text", "")})
            if result.get("schedule_updated"):
                yield _sse({
                    "schedule_updated": True,
                    "termin": result.get("termin", ""),
                    "pushed": result.get("pushed", False),
                })
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
