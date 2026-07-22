from functools import lru_cache

import anthropic

from app.config import get_settings


@lru_cache
def get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=get_settings().anthropic_api_key)


def get_response_text(response) -> str:
    """Extrahiert den Text aus einer Claude-Antwort. `content[0]` ist NICHT
    zuverlässig der Text-Block — bei aktiviertem Thinking steht davor ein
    ThinkingBlock ohne `.text`-Attribut, was `content[0].text` crashen lässt."""
    for block in response.content:
        if block.type == "text":
            return block.text
    return ""


def complete_json(
    prompt: str,
    *,
    system: str = "",
    model: str = "",
    max_tokens: int = 1000,
    disable_thinking: bool = True,
) -> str:
    """Ein Text-Completion-Call ohne Streaming/Tool-Use — zentraler Umschaltpunkt
    zwischen Anthropic-API (claude_engine="api", Default, nutzungsabhängige
    Abrechnung) und Claude-Code-Headless-Modus (claude_engine="cli", Abrechnung
    über Claude-Code-Abo, siehe app.services.claude_cli). Ersetzt an den
    Single-Shot-Stellen (classify.py, memory.py, kunden_status_service.py,
    onboarding_ai.py) get_client().messages.create(...) + get_response_text(...).

    NICHT für den Chat-Endpoint (Streaming + Tool-Use) — siehe
    app.services.claude_cli.stream_chat für den Chat-Loop-Ersatz.
    """
    from app.constants import Models

    settings = get_settings()
    resolved_model = model or Models.SONNET

    if settings.claude_engine == "cli":
        from app.services import claude_cli
        return claude_cli.run_json(prompt, system_prompt=system, model=resolved_model)

    kwargs: dict = {"model": resolved_model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}
    if system:
        kwargs["system"] = system
    if disable_thinking:
        kwargs["thinking"] = {"type": "disabled"}
    resp = get_client().messages.create(**kwargs)
    return get_response_text(resp)
