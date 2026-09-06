"""FastAPI-App des Lead-Agenten - isolierter Container (eigenes
Docker-Netzwerk lead-agent-bridge, siehe docker-compose.yml), analog zu
dev-agent/server.py.

Zwei grundverschiedene Erreichbarkeits-/Auth-Modelle in einem Prozess:
  - /chat, /health: NUR aus dem internen lead-agent-bridge-Netzwerk erreichbar
    (kein Port dieses Containers geht direkt ins Internet außer /lead-agent/webhook/close,
    siehe docker-compose.yml). Auth läuft am Backend-Proxy
    (Depends(get_current_user) in backend/app/routers/lead_agent_proxy.py) -
    genau wie bei dev-agent, hier deshalb bewusst KEIN eigener Auth-Check.
  - /lead-agent/webhook/close: ÖFFENTLICH über einen eigenen, schmalen
    Traefik-Router direkt auf diesen Container erreichbar (docker-compose.yml,
    PathPrefix `/lead-agent/webhook`, bewusst NICHT über Caddy/Backend - Close
    hat keine Cookie-Session). Auth läuft stattdessen über HMAC-Signaturprüfung
    (webhooks.py:verify_signature), fail-closed ohne gesetztes Secret. Als
    Close-Webhook-URL eintragen: https://<DOMAIN>/lead-agent/webhook/close
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import claude_agent
import webhooks

STATIC_DIR = Path(__file__).resolve().parent / "static"
EXPORTS_DIR = STATIC_DIR / "exports"

app = FastAPI(title="Prozessia Lead-Agent")
# Wie dev-agent: unkritisch breiter CORS-Origin, weil /chat/health nur aus dem
# internen Docker-Netzwerk erreichbar sind (kein öffentlicher Port). Gilt
# NICHT für /lead-agent/webhook/close - das läuft über HMAC-Auth, nicht CORS/Cookies.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Export-Dateien aus export_leads.py (Teil C) - NUR intern über
# lead-agent-bridge erreichbar (/static/exports/<datei>, kein öffentlicher
# Port außer /lead-agent/webhook, siehe docker-compose.yml). Öffentlich
# (authentifiziert) ausgeliefert wird darüber ausschließlich der
# Backend-Proxy GET /api/lead-agent/exports/{filename}, siehe
# export_leads.py-Docstring.
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static/exports", StaticFiles(directory=EXPORTS_DIR), name="exports")


@app.on_event("startup")
async def _on_startup() -> None:
    claude_agent.ensure_mcp_approval()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    model: str = claude_agent.DEFAULT_MODEL


@app.post("/chat")
def chat(body: ChatRequest):
    messages = [m.model_dump() for m in body.messages]
    return StreamingResponse(
        claude_agent.stream_chat(messages, body.model),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/ui")
def ui():
    """Eigene, minimale Chat-UI (statisches HTML+JS, kein Build-Schritt) -
    bewusst NICHT ins React-Kundendashboard integriert (siehe
    docs/system-overview-lead-agent.md: 'eigenständig, eigene Route')."""
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/lead-agent/webhook/close")
async def close_webhook(request: Request):
    raw_body = await request.body()
    timestamp = request.headers.get("close-sig-timestamp", "")
    signature = request.headers.get("close-sig-hash", "")
    try:
        webhooks.verify_signature(raw_body, timestamp, signature)
    except webhooks.WebhookAuthError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e

    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail="ungültiges JSON") from e

    return webhooks.handle_payload(payload)
