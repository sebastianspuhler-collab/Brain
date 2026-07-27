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
import asyncio
import fcntl
import json
import os
import pty
import signal
import struct
import subprocess
import termios
import time
from pathlib import Path
from threading import Thread

from fastapi import FastAPI, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

WORKSPACE = Path("/workspace")
CLAUDE_BIN = "claude"
PORT_RANGE = "8100-8120"
DEFAULT_MODEL = "claude-sonnet-5"
ALLOWED_MODELS = {"claude-sonnet-5", "claude-opus-4-8"}
ALLOWED_EFFORTS = {"low", "medium", "high", "xhigh", "max"}

# ── Echtes interaktives Terminal (Umsetzungsplan 2026-07-27) ────────────────
# Sebastian will den Entwicklungs-Agenten "1:1 wie Claude Code" - dafür reicht
# der bisherige Headless-Chat-Pfad (-p, ein frischer Prozess pro Nachricht,
# siehe _stream() unten) nicht: Tool-Aufrufe/Ausgabe sind darin unsichtbar,
# und es gibt keine echten Slash-Commands (/model, /effort, ...). Hier ein
# GENUINE interaktiver `claude`-Prozess pro Sitzung, an ein PTY gebunden,
# per WebSocket 1:1 mit einem echten Terminal im Browser verbunden (gleiches
# Prinzip wie ttyd/Gotty/code-server). Der alte /chat-SSE-Pfad bleibt
# unangetastet bestehen (kein Aufrufer mehr im Frontend, aber kein Grund,
# funktionierenden Code zu entfernen).
IDLE_TIMEOUT_SECONDS = 45 * 60
MAX_SESSION_SECONDS = 4 * 60 * 60
MAX_CONCURRENT_SESSIONS = 3
CLEANUP_INTERVAL_SECONDS = 60


class PtySession:
    def __init__(self, session_id: str, master_fd: int, proc: subprocess.Popen):
        self.session_id = session_id
        self.master_fd = master_fd
        self.proc = proc
        self.created_at = time.monotonic()
        self.last_active = time.monotonic()
        self.cols = 120
        self.rows = 30
        self.ws: WebSocket | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        self.closed = False


SESSIONS: dict[str, PtySession] = {}


def _set_winsize(fd: int, cols: int, rows: int) -> None:
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))


def _apply_resize(session: PtySession, cols: int, rows: int) -> None:
    session.cols, session.rows = max(cols, 1), max(rows, 1)
    try:
        _set_winsize(session.master_fd, session.cols, session.rows)
    except OSError:
        pass


def _nudge_redraw(session: PtySession) -> None:
    """Beim Wiederandocken an eine noch laufende Sitzung (z.B. nach Reload)
    gibt es keinen Scrollback-Verlauf (bewusst nicht Teil dieses Umbaus) - ein
    winziger Größen-Zwitscher erzwingt zuverlässig ein SIGWINCH, worauf die
    meisten Terminal-Apps (auch Claude Codes) den Bildschirm neu zeichnen."""
    c, r = session.cols, session.rows
    _set_winsize(session.master_fd, max(c - 1, 1), r)
    _set_winsize(session.master_fd, c, r)


async def _safe_send_bytes(ws: WebSocket, data: bytes) -> None:
    try:
        await ws.send_bytes(data)
    except Exception:
        pass


def _reader_loop(session: PtySession) -> None:
    """Läuft in einem eigenen Thread (PTY-Reads sind blockierend, passen nicht
    direkt in die asyncio-Loop) - schiebt gelesene Bytes per
    run_coroutine_threadsafe an die aktuell angedockte WebSocket-Verbindung.
    Ist gerade keine verbunden (Nutzer hat die Seite verlassen), werden die
    Bytes verworfen - kein Scrollback-Puffer, siehe Umsetzungsplan."""
    while True:
        try:
            data = os.read(session.master_fd, 4096)
        except OSError:
            break
        if not data:
            break
        ws, loop = session.ws, session.loop
        if ws is not None and loop is not None:
            try:
                fut = asyncio.run_coroutine_threadsafe(_safe_send_bytes(ws, data), loop)
                fut.result(timeout=5)
            except Exception:
                pass
    _terminate_session(session)


def _terminate_session(session: PtySession) -> None:
    if session.closed:
        return
    session.closed = True
    try:
        os.close(session.master_fd)
    except OSError:
        pass
    if session.proc.poll() is None:
        try:
            os.killpg(os.getpgid(session.proc.pid), signal.SIGTERM)
        except (ProcessLookupError, OSError):
            pass
    SESSIONS.pop(session.session_id, None)


def _spawn_session(session_id: str, model: str, effort: str) -> PtySession:
    master_fd, slave_fd = pty.openpty()
    _set_winsize(master_fd, 120, 30)

    # Kein --permission-mode bypassPermissions/--dangerously-skip-permissions:
    # die CLI verweigert das explizit als root ("cannot be used with root/sudo
    # privileges for security reasons" - live beim Deploy-Test aufgefallen).
    # Stattdessen wie im bisherigen Headless-Pfad (_stream() unten) nur ein
    # festes Tool-Whitelist über --allowedTools - lief dort schon als root.
    # Anders als im Headless-Modus kann der Nutzer hier ohnehin live auf einen
    # eventuellen Rückfrage-Prompt reagieren (echtes interaktives Terminal),
    # das ist sogar näher am echten Claude-Code-Gefühl als ein Blanket-Bypass.
    cmd = [
        CLAUDE_BIN,
        "--model", model,
        "--system-prompt", SYSTEM_PROMPT,
        "--add-dir", str(WORKSPACE),
        "--tools", "Bash,Read,Write,Edit,Glob,Grep",
        "--allowedTools", "Bash,Read,Write,Edit,Glob,Grep",
        "--strict-mcp-config",
    ]
    if effort:
        cmd += ["--effort", effort]

    env = _subprocess_env()
    env["TERM"] = "xterm-256color"
    try:
        proc = subprocess.Popen(
            cmd, cwd=str(WORKSPACE), env=env,
            stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
            start_new_session=True, close_fds=True,
        )
    finally:
        os.close(slave_fd)

    session = PtySession(session_id, master_fd, proc)
    Thread(target=_reader_loop, args=(session,), daemon=True).start()
    return session


async def _cleanup_loop() -> None:
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
        now = time.monotonic()
        for session in list(SESSIONS.values()):
            if session.closed:
                continue
            if now - session.last_active > IDLE_TIMEOUT_SECONDS or now - session.created_at > MAX_SESSION_SECONDS:
                _terminate_session(session)


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


@app.on_event("startup")
async def _on_startup() -> None:
    asyncio.create_task(_cleanup_loop())


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


UPLOAD_MAX_BYTES = 50 * 1024 * 1024  # 50 MB - großzügiger als /api/chat/attach
# (reiner Text-Extrakt), hier landet die echte Datei im Workspace.


@app.post("/upload-to-workspace")
async def upload_to_workspace(file: UploadFile):
    """Legt eine Datei direkt in /workspace ab (Umsetzungsplan 2026-07-27) -
    für ein echtes Terminal passt "Text in den Prompt einbetten" nicht mehr,
    der Nutzer soll die Datei per Dateiname referenzieren können (cat, in ein
    Projekt kopieren, ...). Kein Auth-Check hier (wie /chat//health) - dieser
    Container ist nur aus dem internen Docker-Netzwerk erreichbar, die
    Anmeldung läuft am Backend-Proxy."""
    body = await file.read()
    if len(body) > UPLOAD_MAX_BYTES:
        raise HTTPException(status_code=400, detail="Datei zu groß (max. 50 MB)")
    filename = Path(file.filename).name
    target = WORKSPACE / filename
    target.write_bytes(body)
    return {"filename": filename, "path": str(target)}


@app.websocket("/ws/{session_id}")
async def ws_terminal(websocket: WebSocket, session_id: str):
    """Echtes interaktives Terminal (Umsetzungsplan 2026-07-27): verbindet
    einen dauerhaften, an ein PTY gebundenen `claude`-Prozess mit dem Browser.
    Protokoll: Client->Server ausschließlich JSON-Text-Frames
    ({"type":"input","data":"..."} / {"type":"resize","cols":N,"rows":N}),
    Server->Client rohe Terminal-Ausgabe als Binär-Frames (kein Overhead im
    Hot-Path) plus vereinzelte JSON-Text-Frames für Fehler."""
    await websocket.accept()

    model = websocket.query_params.get("model", DEFAULT_MODEL)
    if model not in ALLOWED_MODELS:
        model = DEFAULT_MODEL
    effort = websocket.query_params.get("effort", "")
    if effort not in ALLOWED_EFFORTS:
        effort = ""

    session = SESSIONS.get(session_id)
    reattaching = session is not None and not session.closed and session.proc.poll() is None
    if not reattaching:
        active = sum(1 for s in SESSIONS.values() if not s.closed)
        if active >= MAX_CONCURRENT_SESSIONS:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Zu viele gleichzeitige Entwicklungs-Sitzungen (max. {MAX_CONCURRENT_SESSIONS}). Bitte zuerst eine andere beenden.",
            }))
            await websocket.close()
            return
        try:
            session = _spawn_session(session_id, model, effort)
        except Exception as ex:
            await websocket.send_text(json.dumps({"type": "error", "message": str(ex)}))
            await websocket.close()
            return
        SESSIONS[session_id] = session

    session.ws = websocket
    session.loop = asyncio.get_running_loop()
    session.last_active = time.monotonic()
    if reattaching:
        _nudge_redraw(session)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            session.last_active = time.monotonic()
            msg_type = msg.get("type")
            if msg_type == "input":
                data = msg.get("data", "")
                if data:
                    try:
                        os.write(session.master_fd, data.encode())
                    except OSError:
                        break
            elif msg_type == "resize":
                _apply_resize(session, int(msg.get("cols", session.cols)), int(msg.get("rows", session.rows)))
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if session.ws is websocket:
            session.ws = None
