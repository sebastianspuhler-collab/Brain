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
  - `--permission-mode bypassPermissions` (und `--dangerously-skip-permissions`)
    werden von Claude Code verweigert, wenn der Prozess als root läuft
    ("cannot be used with root/sudo privileges for security reasons") - der
    Backend-Container läuft komplett als root, das brach stream_chat() und
    describe_image() live mit exit 1 ab (leere SSE-Antwort trotz HTTP 200).
    Fix: stattdessen `--allowedTools` mit der exakten Tool-Liste (inkl.
    `mcp__prozessia-tools__*` für die MCP-Tools bei stream_chat()) - das
    umgeht den Root-Guard, weil es einzelne Tools freigibt statt ALLE
    Permission-Checks zu deaktivieren.
  - run_json() (kein Tool-/MCP-Zugriff, `--tools ""`) liefert echte Antworten
    sofort. stream_chat() (mit MCP) braucht das mcp_warmup_seconds-Timing dort
    (siehe Docstring) - ohne das hält das Modell MCP-Tools fälschlich für
    nicht verfügbar, weil es reagiert bevor der MCP-Server verbunden ist.
"""
import json
import os
import signal
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

from app.config import get_settings

CLAUDE_BIN = "claude"


def terminate_process_tree(proc: subprocess.Popen, timeout: float = 3.0) -> None:
    """Beendet proc UND seine komplette Prozessgruppe (MCP-Server-, Subagenten-
    und Tool-Kindprozesse wie `git`, die `claude -p` selbst startet) und wartet
    IMMER danach auf ihn, damit kein Zombie zurückbleibt.

    Bug (2026-08-06, gefunden nach Support-Anfrage "Verbindung bricht ab"):
    der bisherige Cleanup war `if proc.poll() is None: proc.kill()` - das
    killt nur den direkten Kindprozess UND ruft nie proc.wait() danach auf,
    also wird der Zombie nie eingesammelt. Nach einer Woche Chat-Betrieb
    waren so ~4.750 Zombie-Prozesse (fast der komplette Container-Prozesstisch)
    aufgelaufen, dazu mehrere GB RAM in verwaisten, weiterlaufenden
    MCP-Server-/Subagenten-Prozessen - das degradiert den einzigen
    Uvicorn-Worker so weit, dass neue Verbindungen abbrechen/hängen.
    Fix: spawn_process() startet jetzt mit start_new_session=True (eigene
    Prozessgruppe), damit os.killpg() den kompletten Baum trifft statt nur
    proc selbst - und wait() danach reap't ihn tatsächlich."""
    if proc.poll() is not None:
        return
    try:
        pgid = os.getpgid(proc.pid)
        os.killpg(pgid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        proc.wait(timeout=timeout)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        pass  # SIGKILL kann nicht blockiert werden - sollte praktisch nie passieren


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


def spawn_process(
    model: str,
    system_prompt: str,
    max_budget_usd: float = 2.00,
    tools: str | None = None,
    allowed_tools: str | None = None,
) -> subprocess.Popen:
    """Baut den claude -p Subprocess auf (stream-json, MCP-fähig) und startet
    ihn - OHNE den mcp_warmup-Sleep oder das Schreiben der ersten
    stdin-Nachricht, das ist Sache des Aufrufers (stream_chat()'s
    Cold-Start-Pfad, oder claude_cli_pool.py beim Vorwärmen eines
    Standby-Prozesses im Hintergrund). Einzige Quelle für den cmd-Aufbau,
    damit Pool- und Cold-Start-Pfad nicht auseinanderlaufen.

    tools/allowed_tools (Agenten-Berechtigungen, Umsetzungsplan 2026-07-25):
    None => exakt die bisherigen hartcodierten Werte (alle Tools) -
    claude_cli_pool.py's Aufruf bleibt dadurch unverändert 3-Positional-Args
    und byte-identisch zu vorher. Nur wenn ein Agent eingeschränkt ist,
    übergibt der Aufrufer (claude_cli.stream_chat()) hier konkrete Werte.

    KEIN Ordner-Scoping (bewusst, Sebastian 2026-07-25): --add-dir wurde
    live auf dem VPS getestet und schränkt den Datei-Zugriff NICHT wirklich
    ein - ein Prozess mit --allowedTools Read und --add-dir auf einen
    Unterordner konnte trotzdem Dateien außerhalb davon lesen (cwd bleibt
    der ganze Vault, --add-dir ist rein additiv, keine Sandbox). Ein
    Zuständigkeitsbereich läuft deshalb ausschließlich über den
    Zusatz-Prompt (system_prompt_zusatz) - der Agent wird angewiesen, sich
    daran zu halten, es gibt keine technische Durchsetzung. ordner_filter
    bleibt wie bisher nur eine Einschränkung der RAG-Suche."""
    settings = get_settings()
    vault = str(settings.vault_path)
    mcp_config = str(Path(vault) / ".mcp.json")

    # WebSearch (Sebastian, 2026-07-30: "muss auch selbst recherchieren
    # können") - natives Claude-Code-Tool, läuft übers Abo wie alles andere
    # hier, kein separater API-Key/Vendor nötig.
    tools_value = tools if tools is not None else "Read,Write,Edit,Glob,Grep,WebSearch"
    allowed_value = allowed_tools if allowed_tools is not None else "Read,Write,Edit,Glob,Grep,WebSearch,mcp__prozessia-tools__*"

    cmd = [
        CLAUDE_BIN, "-p",
        "--input-format", "stream-json",
        "--output-format", "stream-json",
        "--include-partial-messages",
        "--verbose",
        "--model", model,
        "--system-prompt", system_prompt,
        "--add-dir", vault,
        "--tools", tools_value,
        "--allowedTools", allowed_value,
        "--mcp-config", mcp_config,
        "--strict-mcp-config",
        "--no-session-persistence",
        "--max-budget-usd", str(max_budget_usd),
    ]
    return subprocess.Popen(
        cmd, env=_subprocess_env(), cwd=vault,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1,
        # Eigene Prozessgruppe (Session-Leader) - noetig, damit
        # terminate_process_tree() per os.killpg() den kompletten von `claude`
        # gestarteten Baum (MCP-Server, Subagenten, git-Aufrufe) auf einen
        # Schlag beenden kann statt nur diesen einen Prozess.
        start_new_session=True,
    )


def _merge_prompt(prompt: str, dynamic_context: str) -> str:
    """Baut die erste stdin-Nachricht. dynamic_context (Datum/Aufgaben/
    Kalender/RAG/Kundenkontext/Agent-Zusatz, siehe context.py:
    build_dynamic_context()) landet in einem abgegrenzten <context>-Block vor
    dem eigentlichen Prompt statt im System-Prompt - notwendig, weil ein aus
    dem Pool wiederverwendeter Prozess nur den fixen BASE_PROMPT als
    --system-prompt mitbekommen hat (siehe claude_cli_pool.py)."""
    if not dynamic_context:
        return prompt
    return (
        "<context>\n"
        "Aktueller System-Kontext (Datum, offene Aufgaben, Vault-Struktur, "
        "Kalender, Mails, Suchergebnisse, ggf. Agenten-Zusatzinstruktionen) - "
        "Teil deiner Systemumgebung, keine Nutzeräußerung:\n"
        f"{dynamic_context}\n"
        "</context>\n\n"
        f"{prompt}"
    )


def stream_chat(
    prompt: str,
    system_prompt: str,
    dynamic_context: str = "",
    model: str = "claude-sonnet-5",
    max_budget_usd: float = 2.00,
    timeout: int = 300,
    mcp_warmup_seconds: float = 8.0,
    try_pool: bool = False,
    tools: str | None = None,
    allowed_tools: str | None = None,
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

    WARM POOL (2026-07-24): wenn try_pool=True, wird zuerst versucht, einen
    bereits gestarteten und MCP-verbundenen Standby-Prozess aus
    claude_cli_pool zu bekommen (kein mcp_warmup_seconds-Sleep nötig). Ist
    keiner bereit, greift exakt der bisherige Cold-Start-Pfad. WICHTIG: ein
    Pool-Standby hat beim Vorwärmen NUR BASE_PROMPT (context.py) als
    --system-prompt bekommen, nicht das hier übergebene system_prompt -
    Aufrufer mit try_pool=True müssen deshalb system_prompt=BASE_PROMPT
    übergeben (und den Rest über dynamic_context schicken), sonst laufen
    Cold- und Warm-Pfad mit unterschiedlichen System-Prompts auseinander.

    Yielded rohe, geparste stream-json-Events (dicts). Der Aufrufer in
    chat.py übersetzt diese ins bestehende SSE-Format fürs Frontend.

    AGENTEN-BERECHTIGUNGEN (2026-07-25): tools/allowed_tools sind None,
    solange kein Agent mit allowed_tools aktiv ist - dann bleibt
    effective_try_pool unverändert try_pool, alter Pfad. Ist eins der beiden
    gesetzt (scoped), wird der Pool IMMER umgangen, auch bei try_pool=True:
    ein Standby-Prozess wurde schon beim Vorwärmen mit vollem Tool-Zugriff
    gestartet, bevor der Agent überhaupt bekannt war (siehe
    claude_cli_pool.py) - er kann nachträglich nicht mehr eingeschränkt
    werden. Eingeschränkte Agenten kalt-starten deshalb immer ihren eigenen,
    korrekt begrenzten Prozess und verlieren dafür die ~8-15s
    Pool-Ersparnis - akzeptierter, bewusster Trade-off. (Kein add_dirs-
    Parameter mehr: --add-dir schränkt den Datei-Zugriff live getestet
    NICHT wirklich ein, siehe spawn_process()'s Docstring - ein
    Zuständigkeitsbereich läuft nur über den Zusatz-Prompt.)
    """
    scoped = tools is not None or allowed_tools is not None
    effective_try_pool = try_pool and not scoped

    warm = None
    if effective_try_pool:
        from app.services import claude_cli_pool  # lazy: claude_cli_pool importiert claude_cli

        warm = claude_cli_pool.acquire(model)

    proc = warm.proc if warm is not None else spawn_process(
        model, system_prompt, max_budget_usd, tools=tools, allowed_tools=allowed_tools
    )
    try:
        if warm is None:
            time.sleep(mcp_warmup_seconds)
        text = _merge_prompt(prompt, dynamic_context)
        user_event = {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": text}]}}
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
            stderr = "".join(warm.stderr_tail) if warm is not None else proc.stderr.read()
            raise ClaudeCliError(f"claude -p exit {proc.returncode}: {stderr[:500]}")
    finally:
        terminate_process_tree(proc)
