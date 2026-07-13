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
