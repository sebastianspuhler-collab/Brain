"""Simpler In-Process TTL-Cache. Migriert aus _agent/brain_server.py (_cache/cache_get/cache_set)."""
from datetime import datetime

_cache: dict = {}
DEFAULT_TTL = 300


def get(key: str, ttl: int = DEFAULT_TTL):
    entry = _cache.get(key)
    if entry and (datetime.now() - entry["ts"]).seconds < ttl:
        return entry["data"]
    return None


def set(key: str, data) -> None:
    _cache[key] = {"ts": datetime.now(), "data": data}


def invalidate(key: str) -> None:
    _cache.pop(key, None)
