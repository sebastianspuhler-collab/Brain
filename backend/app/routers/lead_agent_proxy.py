"""Proxy zum isolierten lead-agent-Container (lead-agent/server.py) - exaktes
Vorbild ist der bestehende dev-agent-Proxy (siehe chat.py:
DEV_AGENT_URL/dev_agent_chat()). Das Backend hat selbst KEINEN
Netzwerkzugriff auf den lead-agent-Container außer über diesen einen
HTTP-Aufruf (schmale Brücke lead-agent-bridge, siehe docker-compose.yml).

Auth läuft HIER (Depends(get_current_user), bestehende Cookie-Session) - der
lead-agent-Container selbst hat bewusst KEINEN eigenen Login (siehe
lead-agent/server.py-Docstring), genau wie dev-agent/server.py. Einzige
Ausnahme ist der öffentliche Close-Webhook (/webhooks/close direkt am
lead-agent-Container, NICHT über diesen Proxy - Close hat keine
Cookie-Session, siehe docker-compose.yml Traefik-Labels + lead-agent/webhooks.py).

Bewusst als eigener Router statt in chat.py ergänzt (chat.py ist bereits sehr
groß) - kein Session-Persistenz-Ineinandergreifen mit chat_sessions.py nötig,
der Lead-Agent-Chat ist eigenständig (siehe
docs/system-overview-lead-agent.md: "vorerst nicht ins Kundendashboard
integriert")."""
import json

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from app.deps import get_current_user

router = APIRouter(prefix="/api/lead-agent", tags=["lead-agent"])

LEAD_AGENT_BASE_URL = "http://lead-agent:8000"
LEAD_AGENT_CHAT_URL = f"{LEAD_AGENT_BASE_URL}/chat"
LEAD_AGENT_UI_URL = f"{LEAD_AGENT_BASE_URL}/ui"


class LeadAgentChatMessage(BaseModel):
    role: str
    content: str


class LeadAgentChatRequest(BaseModel):
    messages: list[LeadAgentChatMessage]
    model: str = "claude-sonnet-5"


@router.post("/chat")
async def lead_agent_chat(body: LeadAgentChatRequest, user: str = Depends(get_current_user)):
    messages = [m.model_dump() for m in body.messages]

    async def proxy():
        try:
            async with httpx.AsyncClient(timeout=610.0) as client:
                async with client.stream(
                    "POST", LEAD_AGENT_CHAT_URL, json={"messages": messages, "model": body.model}
                ) as resp:
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            yield f"{line}\n\n"
        except httpx.HTTPError as ex:
            yield f'data: {json.dumps({"error": f"Lead-Agent nicht erreichbar: {ex}"})}\n\n'
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        proxy(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/ui")
async def lead_agent_ui(user: str = Depends(get_current_user)):
    """Reicht die eigenständige, minimale Chat-UI des Lead-Agenten durch -
    bewusst NICHT ins React-Frontend gebaut (siehe
    docs/system-overview-lead-agent.md: 'eigene Route/eigene minimale UI,
    kein Dashboard-Umbau'). Erreichbar unter
    https://brain.prozessia.space/api/lead-agent/ui - läuft über den
    bestehenden Caddy-/api/*-Proxy, keine zusätzliche Traefik-Route nötig
    (siehe README.md 'Warum ein Subpfad statt einer Subdomain')."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(LEAD_AGENT_UI_URL)
        resp.raise_for_status()
        return Response(content=resp.content, media_type="text/html")
    except httpx.HTTPError as ex:
        raise HTTPException(status_code=502, detail=f"Lead-Agent nicht erreichbar: {ex}") from ex


@router.get("/exports/{filename}")
async def lead_agent_export(filename: str, user: str = Depends(get_current_user)):
    """Reicht eine von export_leads() (lead-agent/export_leads.py, Teil C)
    erzeugte CSV/XLSX-Datei durch - Pendant zu lead_agent_ui() oben: auch
    dieser Container hat außer /lead-agent/webhook keine eigene öffentliche
    Traefik-Route (siehe docker-compose.yml), Export-Downloads laufen daher
    genauso über diesen Cookie-auth-gated Proxy statt direkt auf den
    Container. filename wird bewusst NICHT als Pfad interpretiert ('/' bzw.
    '..' werden abgelehnt) - verhindert Path-Traversal auf beliebige Dateien
    im Container über diesen Endpunkt."""
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Ungültiger Dateiname")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{LEAD_AGENT_BASE_URL}/static/exports/{filename}")
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="Export nicht gefunden (evtl. schon nach 24h aufgeräumt)")
        resp.raise_for_status()
    except httpx.HTTPError as ex:
        raise HTTPException(status_code=502, detail=f"Lead-Agent nicht erreichbar: {ex}") from ex

    media_type = "text/csv" if filename.endswith(".csv") else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return Response(
        content=resp.content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
