"""Chat-Endpoint mit SSE-Streaming. Migriert aus brain_server.py:handle_chat()."""
import json
import threading
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.deps import get_current_user
from app.services import context as context_service
from app.services import conversations, memory, rag
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


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    model: str = "claude-sonnet-5"


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _stream_chat(messages: list[dict], model: str):
    if model not in CHAT_MODELS:
        model = "claude-sonnet-5"
    last_msg = messages[-1].get("content", "") if messages else ""
    threading.Thread(target=conversations.log_turn, args=("user", last_msg), daemon=True).start()

    try:
        with ThreadPoolExecutor(max_workers=5) as ex:
            f_system = ex.submit(context_service.build_system)
            f_cust = ex.submit(context_service.get_customer_context, last_msg)
            f_rag = ex.submit(rag.search, last_msg)
            f_mentioned = ex.submit(context_service.get_mentioned_files, messages)
            system = f_system.result()
            cust_ctx = f_cust.result()
            rag_ctx = f_rag.result()
            mentioned_ctx = f_mentioned.result()

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
        _stream_chat(messages, body.model),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
