"""Wrapper um `claude -p` (Claude-Code-Headless-Modus) als Alternative zur
Anthropic Messages API. Abrechnung läuft dann über das Claude-Code-Abo
(CLAUDE_CODE_OAUTH_TOKEN, via `claude setup-token`) statt nutzungsabhängig über
anthropic_api_key - siehe app.config.Settings.claude_engine ("api"/"cli").

Stand 2026-07-23, live gegen einen echten CLAUDE_CODE_OAUTH_TOKEN verifiziert
(vorher nur strukturell, siehe Git-Historie):
  - `--output-format stream-json` braucht zwingend `--verbose` (sonst Fehler).
  - Ist ANTHROPIC_API_KEY in der Prozessumgebung gesetzt, hat er IMMER Vorrang
    vor dem Abo-Token - auch wenn CLAUDE_CODE_OAUTH_TOKEN gesetzt ist, und OHNE
    Fehlermeldung. Muss daher aus der Subprocess-Umgebung entfernt werden.
  - CLAUDE_PROJECT_DIR muss explizit als Env-Var gesetzt werden, sonst kann
    die projekt-lokale .mcp.json ihren eigenen Startbefehl
    (${CLAUDE_PROJECT_DIR}/backend) nicht auflösen (`claude mcp list` zeigt
    das als Warnung).
  - Ein in .mcp.json referenzierter MCP-Server muss einmalig pro Projekt in
    ~/.claude.json (projects[vault_path].enabledMcpjsonServers) freigegeben
    sein - sonst bleibt er für immer "Pending approval", weil der
    Freigabe-Dialog im Headless-Modus (kein TTY) nie erscheint.
  - run_json() (kein Tool-/MCP-Zugriff, `--tools ""`) liefert echte Antworten
    sofort. stream_chat() (mit MCP) braucht das mcp_warmup_seconds-Timing dort
    (siehe Docstring) - ohne das hält das Modell MCP-Tools fälschlich für
    nicht verfügbar, weil es reagiert bevor der MCP-Server verbunden ist.
"""
import json
import os
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

from app.config import get_settings

CLAUDE_BIN = "claude"


def ensure_mcp_approval() -> None:
    """Trägt die MCP-Server-Freigabe für dieses Projekt automatisch in
    ~/.claude.json ein, statt sie über ein Docker-Volume persistieren zu
    müssen - Container werden bei jedem Deploy neu gebaut/neu erstellt,
    ~/.claude.json ist dann leer, und `claude` würde den projekt-lokalen
    MCP-Server (prozessia-tools, siehe .mcp.json) sonst dauerhaft als
    "Pending approval" zeigen (kein TTY im Headless-Modus für den
    Freigabe-Dialog, siehe claude_mcp_list-Befund von der lokalen
    Einrichtung). Idempotent, sicher bei jedem Start aufzurufen - schreibt
    nur, wenn die Freigabe fehlt."""
    settings = get_settings()
    if settings.claude_engine != "cli":
        return
    config_path = Path.home() / ".claude.json"
    vault_key = str(settings.vault_path)
    try:
        data = json.loads(config_path.read_text()) if config_path.exists() else {}
    except (json.JSONDecodeError, OSError):
        data = {}
    projects = data.setdefault("projects", {})
    project = projects.setdefault(vault_key, {})
    enabled = project.setdefault("enabledMcpjsonServers", [])
    if "prozessia-tools" not in enabled:
        enabled.append("prozessia-tools")
    project["hasTrustDialogAccepted"] = True
    config_path.write_text(json.dumps(data, indent=2))


class ClaudeCliError(RuntimeError):
    pass


def _subprocess_env() -> dict:
    """ANTHROPIC_API_KEY muss fehlen, sonst hat er laut Test immer Vorrang vor
    CLAUDE_CODE_OAUTH_TOKEN - stillschweigend, ohne Fehlermeldung.
    CLAUDE_PROJECT_DIR muss explizit gesetzt werden - `claude mcp list` meldet
    sonst "Missing environment variables: CLAUDE_PROJECT_DIR", weil die
    projekt-lokale .mcp.json genau diese Variable im Server-Startbefehl
    referenziert (${CLAUDE_PROJECT_DIR}/backend)."""
    settings = get_settings()
    if not settings.claude_code_oauth_token:
        raise ClaudeCliError(
            "claude_engine=cli, aber claude_code_oauth_token ist nicht gesetzt. "
            "Einmalig `claude setup-token` ausführen (Browser-Login) und den "
            "Token als CLAUDE_CODE_OAUTH_TOKEN in backend/.env eintragen."
        )
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    env["CLAUDE_CODE_OAUTH_TOKEN"] = settings.claude_code_oauth_token
    env["CLAUDE_PROJECT_DIR"] = str(settings.vault_path)
    return env


def run_json(
    prompt: str,
    system_prompt: str = "",
    model: str = "claude-sonnet-5",
    max_budget_usd: float = 0.50,
    timeout: int = 120,
) -> str:
    """Single-Shot-Ersatz für get_client().messages.create(...) +
    get_response_text(...) bei den Stellen ohne Tool-Use (classify.py,
    memory.py, kunden_status_service.py, onboarding_ai.py). Kein Tool-Zugriff
    (--tools ""), kein MCP (--strict-mcp-config ohne --mcp-config), damit
    identisches Verhalten zum bisherigen reinen Text-Completion-Call.
    Gibt den rohen Antworttext zurück (i.d.R. JSON, wie bisher von den
    Aufrufern erwartet)."""
    cmd = [
        CLAUDE_BIN, "-p", prompt,
        "--output-format", "json",
        "--model", model,
        "--system-prompt", system_prompt,
        "--tools", "",
        "--strict-mcp-config",
        "--no-session-persistence",
        "--max-budget-usd", str(max_budget_usd),
    ]
    try:
        result = subprocess.run(
            cmd, env=_subprocess_env(), capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise ClaudeCliError(f"claude -p Timeout nach {timeout}s") from e

    if result.returncode != 0:
        raise ClaudeCliError(f"claude -p exit {result.returncode}: {result.stderr[:500] or result.stdout[:500]}")

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise ClaudeCliError(f"claude -p Ausgabe kein valides JSON: {result.stdout[:300]}") from e

    if data.get("is_error"):
        raise ClaudeCliError(f"claude -p Fehler: {data.get('result', '?')}")

    return data.get("result", "")


def describe_image(
    image_path: str,
    instruction: str,
    model: str = "claude-sonnet-5",
    max_budget_usd: float = 0.50,
    timeout: int = 90,
) -> str:
    """Ersatz für den Base64-Image-Content-Block der Anthropic Messages API
    (inbox.py's Vision-Call) - nutzt stattdessen Claude Codes natives Read-Tool,
    das Bilddateien direkt von der Platte lesen kann. Kein MCP nötig (die Datei
    liegt schon im Inbox-Verzeichnis, bevor dieser Call passiert), daher auch
    kein mcp_warmup-Timing wie bei stream_chat() erforderlich - Read ist ein
    natives Tool und sofort verfügbar."""
    directory = str(Path(image_path).parent)
    cmd = [
        CLAUDE_BIN, "-p", f"Lies die Bilddatei {image_path} und {instruction}",
        "--output-format", "json",
        "--model", model,
        "--add-dir", directory,
        "--tools", "Read",
        "--allowedTools", "Read",
        "--strict-mcp-config",
        "--no-session-persistence",
        "--max-budget-usd", str(max_budget_usd),
    ]
    try:
        result = subprocess.run(
            cmd, env=_subprocess_env(), capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise ClaudeCliError(f"claude -p Timeout nach {timeout}s") from e

    if result.returncode != 0:
        raise ClaudeCliError(f"claude -p exit {result.returncode}: {result.stderr[:500] or result.stdout[:500]}")

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise ClaudeCliError(f"claude -p Ausgabe kein valides JSON: {result.stdout[:300]}") from e

    if data.get("is_error"):
        raise ClaudeCliError(f"claude -p Fehler: {data.get('result', '?')}")

    return data.get("result", "")


def stream_chat(
    prompt: str,
    system_prompt: str,
    model: str = "claude-sonnet-5",
    max_budget_usd: float = 2.00,
    timeout: int = 300,
    mcp_warmup_seconds: float = 8.0,
) -> Iterator[dict]:
    """Streaming-Ersatz für get_client().messages.stream(...) im Chat-Loop
    (chat.py). Nutzt native Claude-Code-Tools (Read/Write/Edit, beschränkt auf
    den Vault-Ordner via --add-dir) statt der Custom-Tools aus tools.py für
    Vault-/Task-Operationen, plus die externen Aktions-Tools aus der
    projekt-lokalen .mcp.json (Buffer/LinkedIn/YouTube/Gmail/Suche).

    Claude Code loopt intern selbst durch mehrere Tool-Aufrufe bis zur finalen
    Antwort - kein manuelles MAX_TOOL_ITERATIONS-Handling wie beim bisherigen
    Anthropic-SDK-Loop nötig.

    MCP-WARMUP (empirisch verifiziert 2026-07-23, live gegen echten
    CLAUDE_CODE_OAUTH_TOKEN): das projekt-lokale MCP ("prozessia-tools", siehe
    .mcp.json) verbindet asynchron im Hintergrund und braucht dafür ~8-13s -
    bei --input-format text (Prompt sofort als Argument) fängt das Modell
    aber sofort an zu antworten und hält die MCP-Tools für "nicht verfügbar",
    wenn es vor Ablauf dieser Zeit reagiert (live beobachtet: Tool fehlte im
    system/init-Event UND wurde vom Modell explizit als nicht vorhanden
    gemeldet). Fix: --input-format stream-json + die eigentliche Nachricht
    erst nach mcp_warmup_seconds über stdin schicken, statt das Timing dem
    Modell zu überlassen - danach zeigt das init-Event zuverlässig
    "status": "connected" und mcp__prozessia-tools__* Tools sind nutzbar.
    Zusätzliche Voraussetzung (einmalig pro Projekt, nicht pro Call): der
    MCP-Server muss in ~/.claude.json unter projects[vault_path].
    enabledMcpjsonServers freigegeben sein - sonst bleibt er dauerhaft
    "Pending approval" (kein TTY im Headless-Modus für den Freigabe-Dialog).

    Yielded rohe, geparste stream-json-Events (dicts). Der Aufrufer in
    chat.py übersetzt diese ins bestehende SSE-Format fürs Frontend.
    """
    settings = get_settings()
    vault = str(settings.vault_path)
    mcp_config = str(Path(vault) / ".mcp.json")

    cmd = [
        CLAUDE_BIN, "-p",
        "--input-format", "stream-json",
        "--output-format", "stream-json",
        "--include-partial-messages",
        "--verbose",
        "--model", model,
        "--system-prompt", system_prompt,
        "--add-dir", vault,
        "--tools", "Read,Write,Edit,Glob,Grep",
        "--allowedTools", "Read,Write,Edit,Glob,Grep,mcp__prozessia-tools__*",
        "--mcp-config", mcp_config,
        "--strict-mcp-config",
        "--no-session-persistence",
        "--max-budget-usd", str(max_budget_usd),
    ]
    proc = subprocess.Popen(
        cmd, env=_subprocess_env(), cwd=vault,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1,
    )
    try:
        time.sleep(mcp_warmup_seconds)
        user_event = {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": prompt}]}}
        proc.stdin.write(json.dumps(user_event) + "\n")
        proc.stdin.flush()
        proc.stdin.close()

        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue
        proc.wait(timeout=timeout)
        if proc.returncode != 0:
            stderr = proc.stderr.read()[:500]
            raise ClaudeCliError(f"claude -p exit {proc.returncode}: {stderr}")
    finally:
        if proc.poll() is None:
            proc.kill()
