"""Wrapper um `claude -p` (Claude-Code-Headless-Modus) als Alternative zur
Anthropic Messages API. Abrechnung läuft dann über das Claude-Code-Abo
(CLAUDE_CODE_OAUTH_TOKEN, via `claude setup-token`) statt nutzungsabhängig über
anthropic_api_key - siehe app.config.Settings.claude_engine ("api"/"cli").

Stand 2026-07-22, empirisch gegen die installierte Claude-Code-CLI (2.1.217)
verifiziert:
  - `--output-format stream-json` braucht zwingend `--verbose` (sonst Fehler).
  - Ist ANTHROPIC_API_KEY in der Prozessumgebung gesetzt, hat er IMMER Vorrang
    vor dem Abo-Token - auch wenn CLAUDE_CODE_OAUTH_TOKEN gesetzt ist, und OHNE
    Fehlermeldung. Muss daher aus der Subprocess-Umgebung entfernt werden.
  - Projekt-lokale .mcp.json wird beim Start korrekt geladen (mcp_servers-Feld
    im ersten "system"/"init"-Event bestätigt das).
NICHT verifiziert: eine echte inhaltliche Antwort Ende-zu-Ende (der zum Testen
verwendete API-Key hatte kein Guthaben mehr - "Credit balance is too low").
Vor dem Umschalten von claude_engine auf "cli" für eine Stelle: einmal live
mit echtem CLAUDE_CODE_OAUTH_TOKEN gegen genau diese Stelle testen.
"""
import json
import os
import subprocess
from collections.abc import Iterator
from pathlib import Path

from app.config import get_settings

CLAUDE_BIN = "claude"


class ClaudeCliError(RuntimeError):
    pass


def _subprocess_env() -> dict:
    """ANTHROPIC_API_KEY muss fehlen, sonst hat er laut Test immer Vorrang vor
    CLAUDE_CODE_OAUTH_TOKEN - stillschweigend, ohne Fehlermeldung."""
    settings = get_settings()
    if not settings.claude_code_oauth_token:
        raise ClaudeCliError(
            "claude_engine=cli, aber claude_code_oauth_token ist nicht gesetzt. "
            "Einmalig `claude setup-token` ausführen (Browser-Login) und den "
            "Token als CLAUDE_CODE_OAUTH_TOKEN in backend/.env eintragen."
        )
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    env["CLAUDE_CODE_OAUTH_TOKEN"] = settings.claude_code_oauth_token
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


def stream_chat(
    prompt: str,
    system_prompt: str,
    model: str = "claude-sonnet-5",
    max_budget_usd: float = 2.00,
    timeout: int = 300,
) -> Iterator[dict]:
    """Streaming-Ersatz für get_client().messages.stream(...) im Chat-Loop
    (chat.py). Nutzt native Claude-Code-Tools (Read/Write/Edit, beschränkt auf
    den Vault-Ordner via --add-dir) statt der Custom-Tools aus tools.py für
    Vault-/Task-Operationen, plus die externen Aktions-Tools aus der
    projekt-lokalen .mcp.json (Buffer/LinkedIn/YouTube/Gmail/Suche).

    Claude Code loopt intern selbst durch mehrere Tool-Aufrufe bis zur finalen
    Antwort - kein manuelles MAX_TOOL_ITERATIONS-Handling wie beim bisherigen
    Anthropic-SDK-Loop nötig.

    Yielded rohe, geparste stream-json-Events (dicts). Der Aufrufer in
    chat.py übersetzt diese ins bestehende SSE-Format fürs Frontend - NICHT
    hier eingebaut, weil das Event-Schema zwar strukturell verifiziert ist
    (system/init, assistant, result), aber Tool-Use-Events selbst mangels
    funktionierendem Test-Guthaben noch nicht live beobachtet wurden.
    """
    settings = get_settings()
    vault = str(settings.vault_path)
    mcp_config = str(Path(vault) / ".mcp.json")

    cmd = [
        CLAUDE_BIN, "-p", prompt,
        "--output-format", "stream-json",
        "--include-partial-messages",
        "--verbose",
        "--model", model,
        "--system-prompt", system_prompt,
        "--add-dir", vault,
        "--tools", "Read,Write,Edit,Glob,Grep",
        "--mcp-config", mcp_config,
        "--strict-mcp-config",
        "--permission-mode", "bypassPermissions",
        "--no-session-persistence",
        "--max-budget-usd", str(max_budget_usd),
    ]
    proc = subprocess.Popen(
        cmd, env=_subprocess_env(), cwd=vault,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1,
    )
    try:
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
