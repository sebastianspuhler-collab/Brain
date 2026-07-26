"""Minimaler Chat-Endpoint für den isolierten Entwickler-Agenten-Container
(Umsetzungsplan 2026-07-25). Eigenständige, bewusst nicht von backend/app
importierte Kopie des SSE-Streaming-Musters aus
backend/app/services/claude_cli.py + backend/app/routers/chat.py - dieser
Service läuft in einem komplett isolierten Container ohne Zugriff auf den
Vault oder den restlichen Backend-Code, daher kein Shared-Code-Import.

Kein Warm-Pool (wie claude_cli_pool.py) und kein MCP-Server (--strict-mcp-config
ohne --mcp-config) - der Dev-Agent braucht keine LinkedIn/Mail/YouTube-Tools,
nur Bash+native Datei-Tools innerhalb von /workspace. Jeder Aufruf startet
einen frischen Subprozess (kein --resume, wie beim Haupt-Chat-Pfad)."""
import json
import os
import subprocess
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

WORKSPACE = Path("/workspace")
CLAUDE_BIN = "claude"
PORT_RANGE = "8100-8120"
DEFAULT_MODEL = "claude-sonnet-5"
ALLOWED_MODELS = {"claude-sonnet-5", "claude-opus-4-8"}

SYSTEM_PROMPT = f"""Du bist der Prozessia-Entwickler-Agent. Du arbeitest
ausschließlich in {WORKSPACE} - das ist dein einziger Zuständigkeitsbereich,
jedes Unterverzeichnis darin ist ein eigenständiges Projekt.

Bei jeder Aufgabe:
1. Sieh dir zuerst per `ls {WORKSPACE}` an, welche Projekte schon existieren.
2. Passt die Aufgabe zu einem bestehenden Projekt, arbeite darin weiter
   (cd hinein). Sonst lege ein neues Unterverzeichnis mit einem sprechenden,
   kurzen Namen an (z.B. {WORKSPACE}/rechner-app) und initialisiere dort ein
   neues Projekt.
3. Nutze Bash frei für npm/pip/git/Build-Tools.
4. Willst du das Ergebnis live zeigbar machen, starte einen Dev-/Preview-Server
   im Hintergrund (z.B. `nohup npm run dev -- --port <PORT> --host 0.0.0.0 > /tmp/dev.log 2>&1 &`)
   auf einem freien Port aus dem Bereich {PORT_RANGE}. Nenne den benutzten Port
   am Ende IMMER explizit und wörtlich in deiner Antwort (z.B. "Läuft auf Port
   8105"), damit daraus ein Link gebaut werden kann - ohne diese Angabe kann
   niemand das Ergebnis sehen.
5. git und gh stehen zur Verfügung, falls ein GitHub-Push gewünscht ist.
"""

app = FastAPI(title="Prozessia Dev-Agent")
# Nur aus dem internen dev-agent-net-Netzwerk erreichbar (siehe docker-compose.yml,
# kein Port dieses Containers ist direkt ins Internet freigegeben) - der breite
# CORS-Origin ist deshalb unkritisch, es ist kein öffentlicher Endpunkt.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatAttachment(BaseModel):
    filename: str
    text: str


class ChatMessage(BaseModel):
    role: str
    content: str
    # Datei-Anhänge nur für diesen Turn (Umsetzungsplan 2026-07-27) - Text kommt
    # vom Backend durchgereicht (backend/app/routers/chat.py::ChatMessage, wird
    # dort bereits über POST /api/chat/attach extrahiert), hier nur noch in den
    # Prompt eingebettet, siehe _format_attachments()/_stream().
    attachments: list[ChatAttachment] | None = None


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    model: str = DEFAULT_MODEL


def _subprocess_env() -> dict:
    token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "")
    if not token:
        raise RuntimeError("CLAUDE_CODE_OAUTH_TOKEN fehlt im Sandbox-Container")
    # Wie claude_cli.py: ANTHROPIC_API_KEY hat sonst stillschweigend Vorrang vor
    # dem Abo-Token.
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    env["CLAUDE_CODE_OAUTH_TOKEN"] = token
    return env


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _format_history(messages: list[dict], budget_chars: int = 12000) -> str:
    """Wie backend/app/routers/chat.py::_format_history() - eigenständig
    implementiert (kein Shared-Import, siehe Datei-Docstring). Jeder Aufruf
    hier ist ein frischer, zustandsloser claude-Subprozess
    (--no-session-persistence, kein --resume) - ohne das würde der Agent bei
    "füg jetzt noch X hinzu" nicht mehr wissen, an welchem Projekt/Kontext er
    gerade war."""
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
    """Wie backend/app/routers/chat.py::_format_attachments() - eigenständig
    implementiert (kein Shared-Import). Nur die Anhänge der letzten (aktuellen)
    Nachricht, nicht aller vorherigen (sonst würde jeder neue Turn erneut den
    vollen Text alter Anhänge mitschleppen)."""
    if not messages:
        return ""
    attachments = messages[-1].get("attachments") or []
    if not attachments:
        return ""
    parts = [f"[ANGEHÄNGTE DATEI: {a.get('filename', '?')}]\n{a.get('text', '')}" for a in attachments]
    return "\n\n".join(parts)


def _stream(messages: list[dict], model: str):
    last_msg = messages[-1]["content"] if messages else ""
    history_block = _format_history(messages)
    attachments_block = _format_attachments(messages)
    prompt = last_msg
    if attachments_block:
        prompt = f"<angehaengte_dateien>\n{attachments_block}\n</angehaengte_dateien>\n\n{prompt}"
    if history_block:
        prompt = f"<bisherige_unterhaltung>\n{history_block}\n</bisherige_unterhaltung>\n\n{prompt}"
    cmd = [
        CLAUDE_BIN, "-p",
        "--input-format", "stream-json",
        "--output-format", "stream-json",
        "--include-partial-messages",
        "--verbose",
        "--model", model,
        "--system-prompt", SYSTEM_PROMPT,
        "--add-dir", str(WORKSPACE),
        "--tools", "Bash,Read,Write,Edit,Glob,Grep",
        "--allowedTools", "Bash,Read,Write,Edit,Glob,Grep",
        "--strict-mcp-config",
        "--no-session-persistence",
        "--max-budget-usd", "3.00",
    ]
    try:
        proc = subprocess.Popen(
            cmd, env=_subprocess_env(), cwd=str(WORKSPACE),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1,
        )
    except Exception as ex:
        yield _sse({"error": str(ex)})
        yield "data: [DONE]\n\n"
        return

    try:
        user_event = {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": prompt}]}}
        proc.stdin.write(json.dumps(user_event) + "\n")
        proc.stdin.flush()
        proc.stdin.close()

        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "assistant":
                for block in event.get("message", {}).get("content", []):
                    if block.get("type") == "text" and block.get("text"):
                        yield _sse({"chunk": block["text"]})
            elif event.get("type") == "result":
                if event.get("is_error"):
                    yield _sse({"error": event.get("result", "Unbekannter Fehler")})
                # Nutzungs-/Kostentracking (Umsetzungsplan 2026-07-27): dieser
                # Container hat keinen Vault-Zugriff und kann usage_log.jsonl
                # nicht selbst schreiben - schickt die Zahlen aus dem
                # result-Event stattdessen als eigenes SSE-Event mit, das
                # backend/app/routers/chat.py::dev_agent_chat abfängt und dort
                # protokolliert.
                yield _sse({"usage": event.get("usage"), "total_cost_usd": event.get("total_cost_usd")})
        proc.wait(timeout=600)
        if proc.returncode != 0:
            stderr = proc.stderr.read()
            yield _sse({"error": f"claude -p exit {proc.returncode}: {stderr[:500]}"})
    except Exception as ex:
        yield _sse({"error": str(ex)})
    finally:
        if proc.poll() is None:
            proc.kill()

    yield "data: [DONE]\n\n"


@app.post("/chat")
def chat(body: ChatRequest):
    messages = [m.model_dump() for m in body.messages]
    model = body.model if body.model in ALLOWED_MODELS else DEFAULT_MODEL
    return StreamingResponse(
        _stream(messages, model),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/health")
def health():
    return {"ok": True}
