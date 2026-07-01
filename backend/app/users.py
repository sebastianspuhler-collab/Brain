"""Nutzerverwaltung. Zwei Personen (Sebastian, Amin) mit gehashten Passwörtern.

Hashes liegen in einer JSON-Datei (users.json: {"sebastian": "$2b$...", "amin": "$2b$..."}),
NICHT in einer ENV-Variable - bcrypt-Hashes enthalten "$"-Zeichen, die docker-compose
in env_file-Werten als Variablen-Interpolation missversteht und stillschweigend kaputt
schreibt. Erzeugen/aktualisieren mit scripts/hash_password.py.
"""
import json
from functools import lru_cache

from app.config import get_settings


@lru_cache
def get_user_hashes() -> dict[str, str]:
    path = get_settings().users_file
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def user_exists(username: str) -> bool:
    return username in get_user_hashes()


def get_password_hash(username: str) -> str | None:
    return get_user_hashes().get(username)
