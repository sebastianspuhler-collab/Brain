"""Chat-Endpoint mit SSE-Streaming. Migriert aus brain_server.py:handle_chat()."""
import json
import threading
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.deps import get_current_user
from app.services import context as context_service
from app.services import agents_service, chat_sessions, conversations, memory, rag
from app.services.anthropic_client import get_client
from app.services.tools import TOOLS, _TASK_TOOL_NAMES, execute_tool

MAX_TOOL_ITERATIONS = 8

router = APIRouter(prefix="/api", tags=["chat"])

CHAT_MODELS = {"claude-sonnet-5", "claude-opus-4-8"}
COMPLEX_KEYWORDS = {
    "analysiere", "analyse", "erkläre", "strategie", "warum",
    "plane", "vergleich", "bewerte", "empfehlung", "überblick",
    "zusammenfassung", "was fehlt", "nächste schritte",
}

# Intelligente Modellauswahl (Umsetzungsplan-Memo 2026-07-16, Token-Nachtrag
# 2026-07-17): kurze, einfache Anfragen automatisch an das deutlich günstigere
# Haiku weiterleiten statt immer Sonnet zu nutzen. Bewusst konservativ - nur
# wenn die Nachricht kurz UND nicht als komplex erkannt ist, UND weder Nutzer
# noch Agent explizit ein teureres Modell gewählt haben (beide Signale werden
# als bewusste Entscheidung respektiert, nie stillschweigend überschrieben).
HAIKU_MODEL = "claude-haiku-4-5-20251001"
SIMPLE_MAX_CHARS = 80


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    model: str = "claude-sonnet-5"
    session_id: str | None = None
    agent_id: str | None = None


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _stream_chat(
    messages: list[dict], model: str, session_id: str | None = None, agent_id: str | None = None
):
    if model not in CHAT_MODELS:
        model = "claude-sonnet-5"
    user_picked_opus = model == "claude-opus-4-8"
    last_msg = messages[-1].get("content", "") if messages else ""
    threading.Thread(target=conversations.log_turn, args=("user", last_msg), daemon=True).start()

    # Eigene benannte Agenten (Umsetzungsplan-Memo 2026-07-16, Punkt D2) - rein
    # optional, ohne agent_id verhält sich der Chat exakt wie zuvor. Ein Agent
    # kann einen Zusatz-Prompt, eine feste Modellwahl und/oder eine Einschränkung
    # der Vault-Suche auf bestimmte Ordner mitbringen.
    agent = agents_service.get_agent(agent_id) if agent_id else None
    agent_forced_model = bool(agent and agent.get("model") in CHAT_MODELS)
    if agent_forced_model:
        model = agent["model"]
    path_prefixes = tuple(agent["ordner_filter"]) if agent and agent.get("ordner_filter") else None

    try:
        with ThreadPoolExecutor(max_workers=5) as ex:
            f_system = ex.submit(context_service.build_system)
            f_cust = ex.submit(context_service.get_customer_context, last_msg)
            f_rag = ex.submit(rag.search_with_sources, last_msg, 15, path_prefixes)
            f_mentioned = ex.submit(context_service.get_mentioned_files, messages)
            system = f_system.result()
            cust_ctx = f_cust.result()
            rag_ctx, rag_sources = f_rag.result()
            mentioned_ctx = f_mentioned.result()

        if agent and agent.get("system_prompt_zusatz"):
            system += f"\n\n=== AGENT: {agent['name']} ===\n{agent['system_prompt_zusatz']}"

        if rag_sources:
            yield _sse({"sources": rag_sources})

        all_raw = "\n\n".join(filter(None, [cust_ctx, rag_ctx, mentioned_ctx]))
        if all_raw:
            synthesis = context_service.synthesize_context(last_msg, all_raw)
            if synthesis:
                system += f"\n\n=== KONTEXT-ANALYSE: VERBINDUNGEN & SCHLÜSSELINFORMATIONEN ===\n{synthesis}"

        if mentioned_ctx:
            system += f"\n\n=== DIREKT REFERENZIERTE DATEIEN ===\n{mentioned_ctx}"
        if cust_ctx:
            system += f"\n\n=== KUNDEN-AKTEN (vollständig) ===\n{cust_ctx}"
        if rag_ctx:
            system += f"\n\n=== RELEVANTE DOKUMENTE & E-MAILS ===\n{rag_ctx}"

        is_complex = (
            any(kw in last_msg.lower() for kw in COMPLEX_KEYWORDS)
            or len(last_msg) > 250
            or model == "claude-opus-4-8"
        )

        is_simple = not is_complex and len(last_msg.strip()) < SIMPLE_MAX_CHARS
        if is_simple and not agent_forced_model and not user_picked_opus:
            model = HAIKU_MODEL

        max_tok = 16000 if model == "claude-opus-4-8" else (8192 if is_complex else 4096)

        # ── Tool-Use-Loop ────────────────────────────────────────────────────
        # Claude bekommt echte Tools (TOOLS-Schema). Solange die Antwort mit
        # stop_reason "tool_use" endet: Tool ausführen, Ergebnis als tool_result
        # zurückschicken, Claude erneut anfragen — bis es fertig ist oder das
        # Iterations-Limit erreicht ist. Migriert aus brain_server.py:handle_chat().
        current_messages = list(messages)
        all_text_parts = []
        tasks_changed = False

        for _iteration in range(MAX_TOOL_ITERATIONS):
            with get_client().messages.stream(
                model=model, max_tokens=max_tok, system=system,
                messages=current_messages, tools=TOOLS,
            ) as stream:
                for chunk in stream.text_stream:
                    all_text_parts.append(chunk)
                    yield _sse({"chunk": chunk})
                final_message = stream.get_final_message()

            current_messages.append({
                "role": "assistant",
                "content": [block.model_dump() for block in final_message.content],
            })

            if final_message.stop_reason != "tool_use":
                break

            tool_result_blocks = []
            for block in final_message.content:
                if block.type != "tool_use":
                    continue
                if block.name in _TASK_TOOL_NAMES:
                    tasks_changed = True
                result_text, is_error = execute_tool(block.name, block.input)
                tool_result_blocks.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_text,
                    "is_error": is_error,
                })
            current_messages.append({"role": "user", "content": tool_result_blocks})
        else:
            yield _sse({"chunk": "\n\n---\n*Hinweis: Maximale Anzahl an Tool-Aufrufen erreicht.*"})

        response_text = "".join(all_text_parts)
        threading.Thread(target=conversations.log_turn, args=("assistant", response_text), daemon=True).start()

        if session_id:
            to_save = messages + [{"role": "assistant", "content": response_text}]
            threading.Thread(
                target=chat_sessions.save_session, args=(session_id, to_save, model), daemon=True
            ).start()

        if tasks_changed:
            yield _sse({"tasks_updated": True})

        saved = memory.auto_remember(last_msg, response_text)
        if saved:
            note = "\n\n---\n*Notiert: " + " | ".join(saved[:2]) + "*"
            yield _sse({"chunk": note})
    except Exception as ex:
        yield _sse({"error": str(ex)})

    yield "data: [DONE]\n\n"


@router.post("/chat")
def chat(body: ChatRequest, user: str = Depends(get_current_user)):
    messages = [m.model_dump() for m in body.messages]
    return StreamingResponse(
        _stream_chat(messages, body.model, body.session_id, body.agent_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Chat-Session-Persistenz (Umsetzungsplan A2) ─────────────────────────────
# Ergänzung: die Kernlogik von /api/chat oben bleibt unverändert, session_id ist
# rein optional. Ohne session_id verhält sich der Chat exakt wie zuvor (kein
# Speichern, kein Laden) - bestehende Aufrufer sind nicht betroffen.

class SaveSessionRequest(BaseModel):
    messages: list[ChatMessage]
    model: str = "claude-sonnet-5"


@router.get("/chat/sessions")
def list_chat_sessions(user: str = Depends(get_current_user)):
    return chat_sessions.list_sessions()


@router.get("/chat/sessions/{session_id}")
def get_chat_session(session_id: str, user: str = Depends(get_current_user)):
    data = chat_sessions.load_session(session_id)
    if data is None:
        return {"id": session_id, "title": "Neuer Chat", "model": "claude-sonnet-5", "messages": []}
    return data


@router.post("/chat/sessions/{session_id}")
def put_chat_session(session_id: str, body: SaveSessionRequest, user: str = Depends(get_current_user)):
    messages = [m.model_dump() for m in body.messages]
    return chat_sessions.save_session(session_id, messages, body.model)


@router.delete("/chat/sessions/{session_id}")
def remove_chat_session(session_id: str, user: str = Depends(get_current_user)):
    chat_sessions.delete_session(session_id)
    return {"ok": True}


# ── Eigene benannte Agenten (Umsetzungsplan-Memo 2026-07-16, Punkt D2) ──────
# Ergänzung: der Hauptchat (ohne agent_id) bleibt exakt wie zuvor. Agenten sind
# zusätzliche, wählbare Chat-Kontexte obendrauf.

class AgentRequest(BaseModel):
    name: str
    system_prompt_zusatz: str = ""
    ordner_filter: list[str] = []
    model: str | None = None


@router.get("/agents")
def list_agents(user: str = Depends(get_current_user)):
    return agents_service.list_agents()


@router.post("/agents")
def create_agent(body: AgentRequest, user: str = Depends(get_current_user)):
    return agents_service.create_agent(
        body.name, body.system_prompt_zusatz, body.ordner_filter, body.model
    )


@router.put("/agents/{agent_id}")
def update_agent(agent_id: str, body: AgentRequest, user: str = Depends(get_current_user)):
    updated = agents_service.update_agent(
        agent_id, body.name, body.system_prompt_zusatz, body.ordner_filter, body.model
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Agent nicht gefunden")
    return updated


@router.delete("/agents/{agent_id}")
def delete_agent(agent_id: str, user: str = Depends(get_current_user)):
    agents_service.delete_agent(agent_id)
    return {"ok": True}
