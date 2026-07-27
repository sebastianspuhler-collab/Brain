"""Chat-Endpoint mit SSE-Streaming. Migriert aus brain_server.py:handle_chat()."""
import asyncio
import base64
import json
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import websockets
from fastapi import APIRouter, Depends, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import get_settings
from app.constants import Models, ALL_MODELS
from app.deps import get_current_user
from app.services import context as context_service
from app.services import agent_capabilities, agents_service, chat_sessions, classify, conversations, memory, rag, usage_service
from app.services import claude_cli
from app.services.anthropic_client import get_client, get_response_text
from app.services.tools import TOOLS, _TASK_TOOL_NAMES, execute_tool

MAX_TOOL_ITERATIONS = 8

router = APIRouter(prefix="/api", tags=["chat"])

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


class ChatAttachment(BaseModel):
    filename: str
    text: str


class ChatMessage(BaseModel):
    role: str
    content: str
    # Datei-Anhänge nur für diesen einen Turn (Umsetzungsplan 2026-07-27) -
    # bewusst NICHT dasselbe wie /api/upload (das indexiert dauerhaft ins
    # Wissen/RAG). Text kommt vom Frontend vorab über POST /api/chat/attach,
    # wird hier nur noch in den Prompt eingebettet, siehe _stream_chat(_cli).
    attachments: list[ChatAttachment] | None = None


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    model: str = Models.SONNET
    session_id: str | None = None
    agent_id: str | None = None


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _format_history(messages: list[dict], budget_chars: int = 12000) -> str:
    """Baut ein Text-Transkript der bisherigen Unterhaltung (alles außer der
    letzten Nachricht) für dynamic_context - der CLI-Pfad (_stream_chat_cli)
    schickt sonst pro Aufruf nur die letzte Nachricht an claude -p
    (--no-session-persistence, kein --resume), Mehrturn-Chats würden sonst
    jeden früheren Kontext verlieren (Umsetzungsplan 2026-07-26). Läuft
    rückwärts ab der vorletzten Nachricht, bis budget_chars erreicht ist, dann
    wieder in chronologischer Reihenfolge - begrenzt das Prompt-Wachstum bei
    langen Unterhaltungen. Ältere Nachrichten bleiben in der Session-Datei
    erhalten, fließen nur nicht mehr in jeden neuen Prompt ein."""
    if len(messages) <= 1:
        return ""
    picked: list[str] = []
    used = 0
    for m in reversed(messages[:-1]):
        role = "Nutzer" if m.get("role") == "user" else "Assistent"
        line = f"{role}: {m.get('content', '')}"
        if used + len(line) > budget_chars and picked:
            break
        picked.append(line)
        used += len(line)
    picked.reverse()
    return "\n\n".join(picked)


def _format_attachments(messages: list[dict]) -> str:
    """Baut den Kontext-Block für Datei-Anhänge der letzten (aktuellen)
    Nachricht (Umsetzungsplan 2026-07-27) - bewusst nur der letzten, nicht
    aller vorherigen Nachrichten, sonst würde jeder neue Turn erneut den
    vollen Text alter Anhänge mitschleppen (Prompt-Wachstum). Der Text bleibt
    trotzdem in der gespeicherten Session erhalten (chat_sessions.py ist
    schema-agnostisch), nur die Wiederverwendung im Prompt ist auf diesen
    Turn begrenzt."""
    if not messages:
        return ""
    attachments = messages[-1].get("attachments") or []
    if not attachments:
        return ""
    parts = [f"[ANGEHÄNGTE DATEI: {a.get('filename', '?')}]\n{a.get('text', '')}" for a in attachments]
    return "\n\n".join(parts)


def _stream_chat(
    messages: list[dict], model: str, session_id: str | None = None, agent_id: str | None = None
):
    if model not in CHAT_MODELS:
        model = Models.SONNET
    user_picked_opus = model == Models.OPUS
    last_msg = messages[-1].get("content", "") if messages else ""
    threading.Thread(target=conversations.log_turn, args=("user", last_msg), daemon=True).start()

    # Sofort-Speichern der Nutzer-Nachricht (Umsetzungsplan 2026-07-26): bisher
    # wurde die Session erst NACH der vollständigen Antwort gespeichert - wer
    # währenddessen wegnavigiert hat, fand den Chat im Verlauf nicht mehr, weil
    # die Datei noch gar nicht existierte. Jetzt existiert die Session schon
    # mit der Nutzer-Nachricht, sobald die Anfrage losläuft; die Antwort
    # überschreibt sie am Ende (siehe unten) mit dem vollständigen Verlauf.
    # Bewusst synchron statt in einem eigenen Thread wie der Abschluss-Save
    # unten - sonst könnte der (parallel gestartete) Abschluss-Save bei sehr
    # kurzen Antworten vor diesem Sofort-Save fertig werden und die
    # vollständige Antwort mit dem Nur-Nutzer-Stand wieder überschreiben.
    if session_id:
        chat_sessions.save_session(session_id, messages, model, agent_id)

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
        attachments_ctx = _format_attachments(messages)
        if attachments_ctx:
            system += f"\n\n=== ANGEHÄNGTE DATEIEN (nur dieser Turn) ===\n{attachments_ctx}"

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
        # Nur role/content an die Anthropic API - "attachments" ist ein reines
        # Zusatzfeld dieser App (siehe ChatMessage oben), die API akzeptiert
        # keine unbekannten Message-Felder (schon einmal live als "Extra
        # inputs are not permitted" mitten im Tool-Use-Loop aufgefallen).
        current_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
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
        # Kein total_cost_usd verfügbar wie beim CLI-Pfad (die Anthropic SDK
        # liefert nur Token-Zahlen, keine Kosten-Schätzung) - Nutzungs-Dashboard
        # zeigt für diesen (inaktiven) Pfad daher 0 $ an, Tokens stimmen.
        usage_service.log_usage("chat", model, usage_totals, cost_usd=None, agent_id=agent_id)

        if session_id:
            to_save = messages + [{"role": "assistant", "content": response_text}]
            threading.Thread(
                target=chat_sessions.save_session, args=(session_id, to_save, model, agent_id), daemon=True
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
      - Behoben (2026-07-26): schickte ursprünglich nur die letzte User-
        Nachricht als Prompt, ohne Erinnerung an frühere Nachrichten. Jetzt
        wird die bisherige Unterhaltung als Text-Transkript in dynamic_context
        eingebettet (siehe _format_history()) - kein echtes --resume/
        Session-Handling im CLI, aber der Prompt enthält den nötigen Kontext.
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

    # Sofort-Speichern der Nutzer-Nachricht (Umsetzungsplan 2026-07-26) - siehe
    # ausführliche Begründung in _stream_chat() oben (bewusst synchron, gegen
    # die Race mit dem parallelen Abschluss-Save-Thread), gilt hier identisch.
    if session_id:
        chat_sessions.save_session(session_id, messages, model, agent_id)

    agent = agents_service.get_agent(agent_id) if agent_id else None
    agent_forced_model = bool(agent and agent.get("model") in CHAT_MODELS)
    if agent_forced_model:
        model = agent["model"]
    path_prefixes = tuple(agent["ordner_filter"]) if agent and agent.get("ordner_filter") else None

    # Agenten-Berechtigungen (Umsetzungsplan 2026-07-25): allowed_tools
    # schränkt --tools/--allowedTools ein. Kein Ordner-Scoping (--add-dir
    # schränkt den echten Datei-Zugriff live getestet NICHT ein, siehe
    # agent_capabilities.py) - ein Zuständigkeitsbereich läuft nur über den
    # Zusatz-Prompt. Bleibt allowed_tools nicht gesetzt, bleibt das
    # Verhalten exakt wie bisher (alle Tools, Pool-Pfad aktiv).
    scoped_tools: str | None = None
    scoped_allowed_tools: str | None = None
    if agent and agent.get("allowed_tools") is not None:
        native_tools, allowed_tool_names = agent_capabilities.expand(agent["allowed_tools"])
        scoped_tools = ",".join(native_tools)
        scoped_allowed_tools = ",".join(allowed_tool_names)

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

        history_block = _format_history(messages)
        if history_block:
            dynamic += f"\n\n=== BISHERIGE UNTERHALTUNG (bereits erledigt, nicht erneut ausführen) ===\n{history_block}"

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
        attachments_ctx = _format_attachments(messages)
        if attachments_ctx:
            dynamic += f"\n\n=== ANGEHÄNGTE DATEIEN (nur dieser Turn) ===\n{attachments_ctx}"

        all_text_parts = []
        tasks_changed = False
        usage_info: dict | None = None
        cost_usd = 0.0
        try:
            for event in claude_cli.stream_chat(
                last_msg,
                system_prompt=context_service.BASE_PROMPT,
                dynamic_context=dynamic,
                model=model,
                try_pool=True,
                tools=scoped_tools,
                allowed_tools=scoped_allowed_tools,
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
                elif etype == "result":
                    if event.get("is_error"):
                        yield _sse({"error": event.get("result", "Unbekannter Fehler")})
                    # Nutzungs-/Kostentracking (Umsetzungsplan 2026-07-27): das
                    # abschließende result-Event der CLI trägt usage/total_cost_usd
                    # unabhängig davon, ob is_error gesetzt ist - bisher wurde das
                    # nirgends ausgelesen.
                    usage_info = event.get("usage")
                    cost_usd = event.get("total_cost_usd") or 0.0
        except claude_cli.ClaudeCliError as e:
            yield _sse({"error": str(e)})

        response_text = "".join(all_text_parts)
        threading.Thread(target=conversations.log_turn, args=("assistant", response_text), daemon=True).start()
        usage_service.log_usage("chat", model, usage_info, cost_usd, agent_id)

        if session_id:
            to_save = messages + [{"role": "assistant", "content": response_text}]
            threading.Thread(
                target=chat_sessions.save_session, args=(session_id, to_save, model, agent_id), daemon=True
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


# ── Datei-Anhänge in Chat-Nachrichten (Umsetzungsplan 2026-07-27) ──────────
# Bewusst getrennt von /api/upload (inbox.py) - das legt Dateien dauerhaft im
# Vault/RAG ab, hier geht es nur um Text-Extraktion für EINEN Chat-Turn, ohne
# irgendetwas zu speichern/indexieren. Nutzt dieselbe classify.extract_text()
# wie die Inbox-Verarbeitung und dieselbe Bild-Transkription wie /api/upload
# (claude_cli.describe_image bzw. Sonnet-Vision-Fallback), aber rein temporär.
ATTACH_MAX_BYTES = 15 * 1024 * 1024  # 15 MB
ATTACH_MAX_CHARS = 20000
_ATTACH_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
_ATTACH_IMAGE_PROMPT = (
    "Extrahiere ALLEN Text und ALLE Zahlen/Daten aus diesem Bild. Formatiere als "
    "sauberen Markdown-Text. Nichts weglassen. Gib NUR den extrahierten Text zurück, "
    "keine Erklärung davor/danach."
)


@router.post("/chat/attach")
async def chat_attach(file: UploadFile, user: str = Depends(get_current_user)):
    body = await file.read()
    if len(body) > ATTACH_MAX_BYTES:
        raise HTTPException(status_code=400, detail="Datei zu groß (max. 15 MB)")

    filename = Path(file.filename).name
    suffix = Path(filename).suffix.lower()
    settings = get_settings()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / filename
        tmp_path.write_bytes(body)

        if suffix in _ATTACH_IMAGE_EXTS:
            try:
                if settings.claude_engine == "cli":
                    text = claude_cli.describe_image(str(tmp_path), _ATTACH_IMAGE_PROMPT)
                else:
                    b64 = base64.standard_b64encode(body).decode()
                    mt = "image/jpeg" if suffix in (".jpg", ".jpeg") else "image/png"
                    vision_result = get_client().messages.create(
                        model=Models.SONNET, max_tokens=2000,
                        thinking={"type": "disabled"},
                        messages=[{"role": "user", "content": [
                            {"type": "image", "source": {"type": "base64", "media_type": mt, "data": b64}},
                            {"type": "text", "text": _ATTACH_IMAGE_PROMPT},
                        ]}],
                    )
                    text = get_response_text(vision_result)
            except Exception as ex:
                raise HTTPException(status_code=400, detail=f"Bild konnte nicht gelesen werden: {ex}") from ex
        else:
            text = classify.extract_text(tmp_path, max_chars=ATTACH_MAX_CHARS)
            if text is None:
                raise HTTPException(status_code=400, detail="Dateiformat wird nicht unterstützt")

    return {"filename": filename, "text": text}


# ── Chat-Session-Persistenz (Umsetzungsplan A2) ─────────────────────────────
# Ergänzung: die Kernlogik von /api/chat oben bleibt unverändert, session_id ist
# rein optional. Ohne session_id verhält sich der Chat exakt wie zuvor (kein
# Speichern, kein Laden) - bestehende Aufrufer sind nicht betroffen.

class SaveSessionRequest(BaseModel):
    messages: list[ChatMessage]
    model: str = Models.SONNET
    agent_id: str | None = None


@router.get("/chat/sessions")
def list_chat_sessions(user: str = Depends(get_current_user)):
    return chat_sessions.list_sessions()


@router.get("/chat/sessions/{session_id}")
def get_chat_session(session_id: str, user: str = Depends(get_current_user)):
    data = chat_sessions.load_session(session_id)
    if data is None:
        return {"id": session_id, "title": "Neuer Chat", "model": Models.SONNET, "messages": [], "agent_id": None}
    return data


@router.post("/chat/sessions/{session_id}")
def put_chat_session(session_id: str, body: SaveSessionRequest, user: str = Depends(get_current_user)):
    messages = [m.model_dump() for m in body.messages]
    return chat_sessions.save_session(session_id, messages, body.model, body.agent_id)


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
    allowed_tools: list[str] | None = None


@router.get("/agents")
def list_agents(user: str = Depends(get_current_user)):
    return agents_service.list_agents()


@router.post("/agents")
def create_agent(body: AgentRequest, user: str = Depends(get_current_user)):
    return agents_service.create_agent(
        body.name, body.system_prompt_zusatz, body.ordner_filter, body.model, body.allowed_tools
    )


@router.put("/agents/{agent_id}")
def update_agent(agent_id: str, body: AgentRequest, user: str = Depends(get_current_user)):
    updated = agents_service.update_agent(
        agent_id, body.name, body.system_prompt_zusatz, body.ordner_filter, body.model,
        body.allowed_tools, allowed_tools_set=True,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Agent nicht gefunden")
    return updated


@router.delete("/agents/{agent_id}")
def delete_agent(agent_id: str, user: str = Depends(get_current_user)):
    agents_service.delete_agent(agent_id)
    return {"ok": True}


@router.get("/agents/{agent_id}/sessions")
def get_agent_sessions(agent_id: str, user: str = Depends(get_current_user)):
    """Chat-Verlauf pro Agent (Umsetzungsplan 2026-07-26): liefert ALLE
    bisherigen Chats für diesen Agenten (nicht nur den neuesten), damit man
    sie im Frontend sehen/fortsetzen/löschen kann. Bewusst OHNE Prüfung, ob
    agent_id in agents_service existiert (anders als die übrigen
    /agents/{id}-Endpunkte) - funktioniert dadurch auch für die reservierte
    "dev-agent"-ID, die kein echter agents.json-Eintrag ist."""
    return chat_sessions.list_sessions_for_agent(agent_id)


# ── Entwickler-Agent-Sandbox (Umsetzungsplan 2026-07-25/26) ─────────────────
# Proxy zum isolierten dev-agent-Container (dev-agent/server.py) - das Backend
# hat selbst KEINEN Datei-/Docker-Zugriff auf die Sandbox, nur diesen einen
# HTTP-Aufruf über das schmale dev-agent-bridge-Netzwerk (siehe
# docker-compose.yml). Kein RAG, kein Agenten-Konzept aus agents_service.py -
# die Sandbox arbeitet in /workspace, nicht im Vault. Die Session-Persistenz
# läuft aber über dieselbe chat_sessions.py wie der normale Chat, getaggt mit
# der reservierten agent_id "dev-agent" (kein echter agents.json-Eintrag) -
# dadurch funktionieren die bestehenden generischen Session-Endpunkte
# (GET/DELETE /api/chat/sessions/{id}) unverändert auch für ihn mit.
DEV_AGENT_URL = "http://dev-agent:8000/chat"
DEV_AGENT_UPLOAD_URL = "http://dev-agent:8000/upload-to-workspace"
DEV_AGENT_ID = "dev-agent"


class DevAgentChatRequest(BaseModel):
    messages: list[ChatMessage]
    model: str = Models.SONNET
    session_id: str | None = None


@router.post("/dev-agent/chat")
async def dev_agent_chat(body: DevAgentChatRequest, user: str = Depends(get_current_user)):
    model = body.model if body.model in CHAT_MODELS else Models.SONNET
    messages = [m.model_dump() for m in body.messages]
    session_id = body.session_id

    # Sofort-Speichern (Umsetzungsplan 2026-07-26): bisher wurde die Session
    # erst nach der vollständigen Antwort geschrieben - bei Aufgaben, die der
    # Entwickler-Agent länger beschäftigen (z.B. ein ganzes Projekt aufsetzen),
    # verschwand der Chat aus dem Verlauf, wenn man währenddessen wegnavigiert
    # ist, weil die Datei noch nicht existierte. Jetzt existiert die Session
    # sofort mit der Nutzer-Nachricht; die Antwort überschreibt sie am Ende.
    # Bewusst synchron (siehe _stream_chat() in dieser Datei für die
    # ausführliche Begründung gegen die Race mit dem Abschluss-Save-Thread).
    if session_id:
        chat_sessions.save_session(session_id, messages, model, DEV_AGENT_ID)

    async def proxy():
        assistant_text = ""
        usage_info: dict | None = None
        cost_usd = 0.0
        try:
            async with httpx.AsyncClient(timeout=610.0) as client:
                async with client.stream(
                    "POST", DEV_AGENT_URL, json={"messages": messages, "model": model}
                ) as resp:
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        yield f"{line}\n\n"
                        payload = line[6:]
                        if payload == "[DONE]":
                            continue
                        try:
                            data = json.loads(payload)
                        except json.JSONDecodeError:
                            continue
                        if data.get("chunk"):
                            assistant_text += data["chunk"]
                        # Nutzungs-/Kostentracking (Umsetzungsplan 2026-07-27) -
                        # der Sandbox-Container hat keinen Vault-Zugriff und kann
                        # usage_log.jsonl daher nicht selbst schreiben, schickt die
                        # Zahlen stattdessen als eigenes SSE-Event mit (siehe
                        # dev-agent/server.py::_stream), das Frontend ignoriert
                        # unbekannte Felder und zeigt es nicht an.
                        if "usage" in data:
                            usage_info = data.get("usage")
                            cost_usd = data.get("total_cost_usd") or 0.0
        except httpx.HTTPError as ex:
            yield f'data: {json.dumps({"error": f"Entwickler-Agent nicht erreichbar: {ex}"})}\n\n'
            yield "data: [DONE]\n\n"
            return

        usage_service.log_usage("dev-agent", model, usage_info, cost_usd, DEV_AGENT_ID)

        if session_id and assistant_text:
            to_save = messages + [{"role": "assistant", "content": assistant_text}]
            threading.Thread(
                target=chat_sessions.save_session,
                args=(session_id, to_save, model, DEV_AGENT_ID),
                daemon=True,
            ).start()

    return StreamingResponse(
        proxy(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/dev-agent/upload")
async def dev_agent_upload(file: UploadFile, user: str = Depends(get_current_user)):
    """Proxy zu dev-agent/server.py::upload_to_workspace() (Umsetzungsplan
    2026-07-27) - der Container ist nur intern erreichbar, siehe Docstring
    oben. Legt die Datei direkt in /workspace ab (kein Text-Extrakt wie
    /api/chat/attach - im echten Terminal referenziert man die Datei per
    Dateiname statt sie als Prompt-Kontext zu bekommen)."""
    body = await file.read()
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                DEV_AGENT_UPLOAD_URL,
                files={"file": (file.filename, body, file.content_type)},
            )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as ex:
        raise HTTPException(status_code=502, detail=f"Entwickler-Agent nicht erreichbar: {ex}") from ex


# ── Echtes interaktives Terminal (Umsetzungsplan 2026-07-27) ────────────────
# "1:1 wie Claude Code" statt der Chat-Simulation oben (/dev-agent/chat, alter
# Pfad bleibt bestehen, hat aber keinen Aufrufer mehr im Frontend): reine
# Byte-Weiterleitung zwischen dem Browser und dev-agent/server.py's
# WebSocket-Endpunkt (dort läuft der dauerhafte, an ein PTY gebundene
# `claude`-Prozess - dieses Backend hier macht nur Auth + Relay, kein
# eigener Zustand). Caddy leitet WebSocket-Upgrades unter /api/* automatisch
# durch, keine Sonderkonfiguration nötig.
DEV_AGENT_WS_URL = "ws://dev-agent:8000/ws"


@router.websocket("/ws/dev-agent/{session_id}")
async def dev_agent_terminal(websocket: WebSocket, session_id: str):
    try:
        user = get_current_user(websocket)
    except HTTPException:
        await websocket.close(code=4401)
        return

    await websocket.accept()

    model = websocket.query_params.get("model", Models.SONNET)
    effort = websocket.query_params.get("effort", "")
    upstream_url = f"{DEV_AGENT_WS_URL}/{session_id}?model={model}&effort={effort}"

    try:
        async with websockets.connect(upstream_url, max_size=None) as upstream:
            async def browser_to_upstream():
                try:
                    while True:
                        text = await websocket.receive_text()
                        await upstream.send(text)
                except WebSocketDisconnect:
                    pass
                except Exception:
                    pass

            async def upstream_to_browser():
                try:
                    async for message in upstream:
                        if isinstance(message, bytes):
                            await websocket.send_bytes(message)
                        else:
                            await websocket.send_text(message)
                except Exception:
                    pass

            task1 = asyncio.ensure_future(browser_to_upstream())
            task2 = asyncio.ensure_future(upstream_to_browser())
            done, pending = await asyncio.wait({task1, task2}, return_when=asyncio.FIRST_COMPLETED)
            for t in pending:
                t.cancel()
    except Exception as ex:
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": f"Entwickler-Agent nicht erreichbar: {ex}"}))
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
