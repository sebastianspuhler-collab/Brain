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


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class UpdatePostRequest(BaseModel):
    text: str


@router.get("/ideas")
def ideas(user: str = Depends(get_current_user)):
    return linkedin_service.get_ideas()


@router.get("/posts")
def posts(status: str | None = None, user: str = Depends(get_current_user)):
    """status=draft|scheduled liefert den echten Live-Buffer-Stand (Grundlage
    für die Entwürfe-/Geplant-Tabs) - ohne status weiterhin die alte, rein
    lokal generierte Liste (Kompatibilität, aktuell ungenutzt vom Frontend)."""
    if status in ("draft", "scheduled"):
        return linkedin_service.get_merged_posts_by_status(status)
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


@router.post("/chat")
def linkedin_chat(body: ChatRequest, user: str = Depends(get_current_user)):
    """Agentischer Chat für die gesamte LinkedIn-Sektion (Ideen, Posts,
    Karusselle, Richtung) - siehe linkedin_service.chat_linkedin_stream().

    Echtes Streaming (2026-08-13, Bugfix): vorher wurde chat_linkedin()
    komplett synchron bis zum Ende des gesamten Turns abgewartet (inkl. aller
    Tool-Aufrufe, z.B. mehrerer Karusselle à 1-2 Min.) und erst dann EIN SSE-
    Event geschickt - die Verbindung blieb so lange komplett still, bis eine
    Zwischenschicht (Traefik/Caddy/Browser) sie mangels Daten kappte
    ("Verbindung bricht ab", Sebastian 13.08.2026). Jetzt wird jedes vom
    Generator gelieferte Event sofort weitergereicht."""
    def stream():
        messages = [m.model_dump() for m in body.messages]
        try:
            for event in linkedin_service.chat_linkedin_stream(messages):
                yield _sse(event)
        except Exception as ex:
            yield _sse({"error": str(ex)})
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/carousels")
def carousels(user: str = Depends(get_current_user)):
    return linkedin_service.get_carousels()


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
