"""Chat-Endpoint mit SSE-Streaming. Migriert aus brain_server.py:handle_chat()."""
import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import get_settings
from app.constants import ALL_MODELS, Models
from app.deps import get_current_user
from app.services import context as context_service
from app.services import agents_service, chat_sessions, conversations, memory, rag
from app.services import claude_cli
from app.services.anthropic_client import get_client
from app.services.tools import TOOLS, _TASK_TOOL_NAMES, execute_tool

MAX_TOOL_ITERATIONS = 8

router = APIRouter(prefix="/api", tags=["chat"])
_usage_logger = logging.getLogger("model_usage")

CHAT_MODELS = {Models.SONNET, Models.OPUS}
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
HAIKU_MODEL = Models.HAIKU
SIMPLE_MAX_CHARS = 80


def _setup_usage_logger() -> None:
    """Modellauswahl-Überarbeitung (Sebastian, 2026-07-18): pro Chat-Anfrage
    Modell + Tokenverbrauch in einer eigenen Log-Datei festhalten, damit
    Kosten nachvollziehbar sind, statt sie nur zu schätzen."""
    if _usage_logger.handlers:
        return
    log_path = get_settings().agent_dir / "model_usage.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    _usage_logger.addHandler(handler)
    _usage_logger.setLevel(logging.INFO)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    model: str = Models.SONNET
    session_id: str | None = None
    agent_id: str | None = None


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _stream_chat(
    messages: list[dict], model: str, session_id: str | None = None, agent_id: str | None = None
):
    if model not in CHAT_MODELS:
        model = Models.SONNET
    user_picked_opus = model == Models.OPUS
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
            or model == Models.OPUS
        )

        is_simple = not is_complex and len(last_msg.strip()) < SIMPLE_MAX_CHARS
        if is_simple and not agent_forced_model and not user_picked_opus:
            model = HAIKU_MODEL

        # Technische Absicherung (Sebastian, 2026-07-18): letzte Prüfung direkt
        # vor dem API-Call, statt einen ungeprüften Modellstring durchzureichen
        # (z.B. falls ein korrupter Agent-Datensatz einmal an CHAT_MODELS
        # vorbeigerutscht wäre). Fällt im Zweifel auf Sonnet zurück.
        if model not in ALL_MODELS:
            model = Models.SONNET

        max_tok = 16000 if model == Models.OPUS else (8192 if is_complex else 4096)

        # ── Tool-Use-Loop ────────────────────────────────────────────────────
        # Claude bekommt echte Tools (TOOLS-Schema). Solange die Antwort mit
        # stop_reason "tool_use" endet: Tool ausführen, Ergebnis als tool_result
        # zurückschicken, Claude erneut anfragen — bis es fertig ist oder das
        # Iterations-Limit erreicht ist. Migriert aus brain_server.py:handle_chat().
        current_messages = list(messages)
        all_text_parts = []
        tasks_changed = False
        usage_totals = {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0}

        for _iteration in range(MAX_TOOL_ITERATIONS):
            with get_client().messages.stream(
                model=model, max_tokens=max_tok, system=system,
                messages=current_messages, tools=TOOLS,
            ) as stream:
                for chunk in stream.text_stream:
                    all_text_parts.append(chunk)
                    yield _sse({"chunk": chunk})
                final_message = stream.get_final_message()
                usage = final_message.usage
                usage_totals["input_tokens"] += usage.input_tokens or 0
                usage_totals["output_tokens"] += usage.output_tokens or 0
                usage_totals["cache_read_input_tokens"] += getattr(usage, "cache_read_input_tokens", 0) or 0

            current_messages.append({
                "role": "assistant",
                # exclude_none: die SDK liefert Content-Blöcke teils als
                # ParsedTextBlock mit einem internen "parsed_output"-Feld
                # (None, SDK-intern für strukturierte Outputs gedacht - siehe
                # ParsedTextBlock.__api_exclude__ in anthropic/types/parsed_message.py),
                # das model_dump() aber trotzdem mitschickt. Die API lehnt dieses
                # unbekannte Feld beim erneuten Einreichen mit 400 ab ("Extra
                # inputs are not permitted") - live beobachtet als "Verbindung
                # unterbrochen" mitten im Tool-Use-Loop.
                "content": [block.model_dump(exclude_none=True) for block in final_message.content],
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
        _setup_usage_logger()
        _usage_logger.info(
            "model=%s input_tokens=%d output_tokens=%d cache_read_input_tokens=%d",
            model,
            usage_totals["input_tokens"],
            usage_totals["output_tokens"],
            usage_totals["cache_read_input_tokens"],
        )

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


def _stream_chat_cli(
    messages: list[dict], model: str, session_id: str | None = None, agent_id: str | None = None
):
    """CLI-Headless-Variante von _stream_chat (claude_engine="cli") - identischer
    Kontext-Aufbau (RAG/Kunden-Akte/Memory-Synthese/Modellwahl), aber der
    Tool-Use-Loop läuft über claude_cli.stream_chat() (Claude-Code-Subprocess,
    Abo-Billing über CLAUDE_CODE_OAUTH_TOKEN) statt über die Anthropic Messages
    API + tools.py-Dispatcher. Vault-Zugriff läuft nativ über Claude Codes
    Read/Write/Edit/Glob/Grep (--add-dir), externe Aktionen (Buffer/LinkedIn/
    YouTube/Gmail/Suche) über die projekt-lokale .mcp.json.

    STATUS (2026-07-22) — NICHT production-ready, bewusst nur hinter
    claude_engine="cli" erreichbar (Default bleibt "api", unverändertes
    Verhalten):
      - Strukturell fertig und gegen das empirisch verifizierte stream-json-
        Event-Schema gebaut (system/init, assistant mit content-Blöcken im
        bekannten Anthropic-Message-Format, result). NICHT live mit einer
        echten Antwort durchgespielt (Test-API-Key ohne Guthaben).
      - WICHTIGE LÜCKE: schickt nur die letzte User-Nachricht als Prompt,
        NICHT die volle messages-History wie der API-Pfad. Mehrturn-Chats
        würden dadurch früheren Kontext verlieren. Für echten Mehrturn-
        Betrieb noch zu lösen (z.B. über --resume/--session-id oder
        --input-format stream-json mit voller History).
      - Tool-Use-Erkennung für tasks_changed ist eine Annahme (Feldname
        "file_path" bei Edit/Write) - nicht gegen einen echten Tool-Aufruf
        bestätigt.
      - Granularität von --include-partial-messages (Token-für-Token vs.
        blockweise) nicht beobachtet - aktuell werden nur komplette
        "assistant"-Content-Blöcke als Chunk behandelt, was im schlechtesten
        Fall gröber wirkt als der jetzige Token-Stream.
    Vor dem Umschalten auf claude_engine="cli": echten CLAUDE_CODE_OAUTH_TOKEN
    setzen, hier live gegen mehrere Nachrichten inkl. Tool-Nutzung testen,
    diesen Kommentar aktualisieren.

    UPDATE (2026-07-24): claude_engine="cli" ist seit 2026-07-23 produktiv
    (siehe .env). Der bisher komplett dynamisch gebaute System-Prompt wird
    jetzt in BASE_PROMPT (fix, für den Warm-Pool) und dynamic_context
    (Datum/Aufgaben/RAG/Kundenkontext/Agent-Zusatz, wechselt bei jeder
    Anfrage) aufgeteilt, siehe context_service.build_dynamic_context() und
    claude_cli_pool.py. Die oben genannten Lücken (Mehrturn-History,
    tasks_changed-Erkennung, Partial-Message-Granularität) bestehen
    unverändert fort - nicht Teil des Pool-Umbaus.
    """
    if model not in CHAT_MODELS:
        model = Models.SONNET
    last_msg = messages[-1].get("content", "") if messages else ""
    threading.Thread(target=conversations.log_turn, args=("user", last_msg), daemon=True).start()

    agent = agents_service.get_agent(agent_id) if agent_id else None
    agent_forced_model = bool(agent and agent.get("model") in CHAT_MODELS)
    if agent_forced_model:
        model = agent["model"]
    path_prefixes = tuple(agent["ordner_filter"]) if agent and agent.get("ordner_filter") else None

    try:
        with ThreadPoolExecutor(max_workers=5) as ex:
            f_system = ex.submit(context_service.build_dynamic_context)
            f_cust = ex.submit(context_service.get_customer_context, last_msg)
            f_rag = ex.submit(rag.search_with_sources, last_msg, 15, path_prefixes)
            f_mentioned = ex.submit(context_service.get_mentioned_files, messages)
            dynamic = f_system.result()
            cust_ctx = f_cust.result()
            rag_ctx, rag_sources = f_rag.result()
            mentioned_ctx = f_mentioned.result()

        if agent and agent.get("system_prompt_zusatz"):
            dynamic += f"\n\n=== AGENT: {agent['name']} ===\n{agent['system_prompt_zusatz']}"

        if rag_sources:
            yield _sse({"sources": rag_sources})

        all_raw = "\n\n".join(filter(None, [cust_ctx, rag_ctx, mentioned_ctx]))
        if all_raw:
            synthesis = context_service.synthesize_context(last_msg, all_raw)
            if synthesis:
                dynamic += f"\n\n=== KONTEXT-ANALYSE: VERBINDUNGEN & SCHLÜSSELINFORMATIONEN ===\n{synthesis}"

        if mentioned_ctx:
            dynamic += f"\n\n=== DIREKT REFERENZIERTE DATEIEN ===\n{mentioned_ctx}"
        if cust_ctx:
            dynamic += f"\n\n=== KUNDEN-AKTEN (vollständig) ===\n{cust_ctx}"
        if rag_ctx:
            dynamic += f"\n\n=== RELEVANTE DOKUMENTE & E-MAILS ===\n{rag_ctx}"

        all_text_parts = []
        tasks_changed = False
        try:
            for event in claude_cli.stream_chat(
                last_msg,
                system_prompt=context_service.BASE_PROMPT,
                dynamic_context=dynamic,
                model=model,
                try_pool=True,
            ):
                etype = event.get("type")
                if etype == "assistant":
                    for block in event.get("message", {}).get("content", []):
                        if block.get("type") == "text" and block.get("text"):
                            chunk = block["text"]
                            all_text_parts.append(chunk)
                            yield _sse({"chunk": chunk})
                        elif block.get("type") == "tool_use":
                            tool_path = str(block.get("input", {}).get("file_path", ""))
                            if "context.md" in tool_path:
                                tasks_changed = True
                elif etype == "result" and event.get("is_error"):
                    yield _sse({"error": event.get("result", "Unbekannter Fehler")})
        except claude_cli.ClaudeCliError as e:
            yield _sse({"error": str(e)})

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
    engine = get_settings().claude_engine
    generator = (
        _stream_chat_cli(messages, body.model, body.session_id, body.agent_id)
        if engine == "cli"
        else _stream_chat(messages, body.model, body.session_id, body.agent_id)
    )
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Chat-Session-Persistenz (Umsetzungsplan A2) ─────────────────────────────
# Ergänzung: die Kernlogik von /api/chat oben bleibt unverändert, session_id ist
# rein optional. Ohne session_id verhält sich der Chat exakt wie zuvor (kein
# Speichern, kein Laden) - bestehende Aufrufer sind nicht betroffen.

class SaveSessionRequest(BaseModel):
    messages: list[ChatMessage]
    model: str = Models.SONNET


@router.get("/chat/sessions")
def list_chat_sessions(user: str = Depends(get_current_user)):
    return chat_sessions.list_sessions()


@router.get("/chat/sessions/{session_id}")
def get_chat_session(session_id: str, user: str = Depends(get_current_user)):
    data = chat_sessions.load_session(session_id)
    if data is None:
        return {"id": session_id, "title": "Neuer Chat", "model": Models.SONNET, "messages": []}
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
