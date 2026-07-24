"""Warmer Standby-Pool für claude_cli.stream_chat()'s MCP-Pfad (2026-07-24).

Jede Chat-Nachricht spawnte bisher einen frischen `claude -p` Subprozess, der
sich erst mit der projekt-lokalen .mcp.json verbinden musste (~8-13s, siehe
claude_cli.py). Statt das während der Nutzer wartet zu überbrücken, hält
dieser Pool pro Modell (Sonnet/Opus - die einzigen beiden über den
CLI-Pfad wählbaren Modelle, siehe chat.py CHAT_MODELS) einen bereits
gestarteten, MCP-verbundenen Standby-Prozess bereit. claude_cli.stream_chat()
holt sich bei try_pool=True zuerst hier einen ab (acquire()); ist keiner
bereit, fällt der Aufrufer automatisch auf den bisherigen Cold-Start-Pfad
zurück - das Verhalten wird also nie schlechter als heute, nur manchmal
besser.

Ein Standby-Prozess bekommt beim Vorwärmen nur context.BASE_PROMPT als
--system-prompt mit (der einzige wirklich statische Teil des Prompts, siehe
context.py:build_dynamic_context()) - alles Dynamische (Datum, Aufgaben,
Kalender, RAG-Treffer, ...) verschickt der Aufrufer erst nach dem Abholen als
Teil der ersten stdin-Nachricht (claude_cli._merge_prompt()).

Nach Vorbild von rag.py's dediziertem Worker-Thread (queue.Queue statt
asyncio.Queue): die Chat-Route ist sync und läuft im Starlette-Threadpool,
nicht im Event-Loop, und Popen()/sleep() blockieren ohnehin - ein
asyncio-Task wäre hier falsch.
"""
import logging
import queue
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass, field

from app.constants import Models
from app.services import claude_cli
from app.services.context import BASE_PROMPT

logger = logging.getLogger("brain.claude_cli_pool")

POOL_TARGET_SIZE = 1
IDLE_EXPIRY_SECONDS = 15 * 60
MAINTENANCE_INTERVAL_SECONDS = 5
WARM_MCP_SECONDS = 15.0
POOL_MAX_BUDGET_USD = 2.00
SPAWN_BACKOFF_CAP_SECONDS = 60


@dataclass
class WarmProcess:
    proc: subprocess.Popen
    model: str
    ready_at: float = 0.0
    stderr_tail: deque = field(default_factory=lambda: deque(maxlen=50))


_pools: dict[str, "queue.Queue[WarmProcess]"] = {
    Models.SONNET: queue.Queue(),
    Models.OPUS: queue.Queue(),
}
_stop_event = threading.Event()
_wake_event = threading.Event()
_maintainer_thread: threading.Thread | None = None
_start_lock = threading.Lock()
_last_spawn_failure: dict[str, float] = {}
_spawn_backoff: dict[str, float] = {}


def start() -> None:
    """Idempotent - sicher bei jedem App-Start aufzurufen (main.py:lifespan)."""
    global _maintainer_thread
    with _start_lock:
        if _maintainer_thread and _maintainer_thread.is_alive():
            return
        _stop_event.clear()
        _maintainer_thread = threading.Thread(
            target=_maintain_loop, daemon=True, name="claude-cli-pool-maintainer"
        )
        _maintainer_thread.start()


def stop() -> None:
    """Beendet die Wartungsschleife und killt alle wartenden Standby-Prozesse -
    verhindert verwaiste `claude`-Prozesse bei Server-Neustarts."""
    _stop_event.set()
    _wake_event.set()
    for q in _pools.values():
        while True:
            try:
                wp = q.get_nowait()
            except queue.Empty:
                break
            _terminate(wp)
    if _maintainer_thread:
        _maintainer_thread.join(timeout=5)


def acquire(model: str) -> WarmProcess | None:
    """Nicht-blockierend: gibt einen lebenden Standby zurück oder None, wenn
    keiner bereit ist (Aufrufer fällt dann auf Cold-Start zurück)."""
    q = _pools.get(model)
    if q is None:
        return None
    while True:
        try:
            wp = q.get_nowait()
        except queue.Empty:
            return None
        if wp.proc.poll() is None:
            _wake_event.set()  # sofortiges Nachfüllen anstoßen statt bis zu 5s zu warten
            return wp
        # zwischenzeitlich gestorben - verwerfen, nächsten Eintrag probieren


def _maintain_loop() -> None:
    while not _stop_event.is_set():
        for model, q in _pools.items():
            _reap_dead_and_expired(q)
            _refill(model, q)
        _wake_event.wait(MAINTENANCE_INTERVAL_SECONDS)
        _wake_event.clear()


def _reap_dead_and_expired(q: "queue.Queue[WarmProcess]") -> None:
    kept = []
    while True:
        try:
            wp = q.get_nowait()
        except queue.Empty:
            break
        if wp.proc.poll() is not None:
            continue
        if time.monotonic() - wp.ready_at > IDLE_EXPIRY_SECONDS:
            _terminate(wp)
            continue
        kept.append(wp)
    for wp in kept:
        q.put(wp)


def _refill(model: str, q: "queue.Queue[WarmProcess]") -> None:
    backoff_until = _last_spawn_failure.get(model, 0.0) + _spawn_backoff.get(model, 0.0)
    if time.monotonic() < backoff_until:
        return
    while q.qsize() < POOL_TARGET_SIZE:
        wp = _spawn_and_warm(model)
        if wp is None:
            _last_spawn_failure[model] = time.monotonic()
            _spawn_backoff[model] = min(SPAWN_BACKOFF_CAP_SECONDS, max(5.0, _spawn_backoff.get(model, 0.0) * 2))
            return
        _spawn_backoff[model] = 0.0
        q.put(wp)


def _spawn_and_warm(model: str) -> WarmProcess | None:
    try:
        proc = claude_cli.spawn_process(model, BASE_PROMPT, POOL_MAX_BUDGET_USD)
    except Exception:
        logger.exception("claude_cli_pool: Spawn fehlgeschlagen für model=%s", model)
        return None
    wp = WarmProcess(proc=proc, model=model)
    threading.Thread(
        target=_drain_stderr, args=(proc, wp.stderr_tail),
        daemon=True, name=f"claude-cli-pool-stderr-{proc.pid}",
    ).start()
    time.sleep(WARM_MCP_SECONDS)
    if proc.poll() is not None:
        logger.warning("claude_cli_pool: Standby während Warmup gestorben, model=%s", model)
        return None
    wp.ready_at = time.monotonic()
    return wp


def _drain_stderr(proc: subprocess.Popen, tail: deque) -> None:
    """Liest stderr eines Standby-Prozesses kontinuierlich mit, solange er
    ungenutzt in der Queue liegt - ohne das würde ein Prozess bei genug
    stderr-Output am vollen OS-Pipe-Buffer hängen bleiben (blockiert, aber
    proc.poll() meldet fälschlich weiter "lebt noch")."""
    try:
        for line in proc.stderr:
            tail.append(line)
    except Exception:
        pass


def _terminate(wp: WarmProcess) -> None:
    if wp.proc.poll() is None:
        wp.proc.kill()
    try:
        wp.proc.wait(timeout=2)
    except Exception:
        pass
