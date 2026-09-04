"""Dünner HTTP-Client für api.close.com/api/v1 - Basic-Auth mit dem API-Key
als Username (Close-Konvention, kein Passwort). Deckt genau die Objekte ab,
die der Lead-Agent braucht: Leads, Contacts, Opportunities, Activities/Notes,
Custom Fields (siehe docs/system-overview-lead-agent.md Punkt 3).

Kein ORM/Wrapper-Framework - reine Funktionen, die dicts zurückgeben (gleiches
Muster wie backend/app/services/gmail_client.py). Retry mit Backoff nur für
transiente Fehler (429 Rate-Limit, 5xx) - ein 4xx (z.B. falscher API-Key,
falsche Lead-ID) ist ein permanenter Fehler und wird sofort als Exception
durchgereicht, kein stilles Wiederholen (gleiches "fail-open bei transienten
Fehlern, nie stillschweigend cachen"-Prinzip wie email_lead_service.py)."""
import time

import httpx

from config import get_settings

_MAX_RETRIES = 3
_RETRY_STATUS = {429, 500, 502, 503, 504}


class CloseAPIError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Close API {status_code}: {detail}")


def _client() -> httpx.Client:
    settings = get_settings()
    return httpx.Client(
        base_url=settings.close_api_base,
        auth=(settings.close_api_key, ""),
        timeout=30.0,
    )


def _request(method: str, path: str, **kwargs) -> dict:
    settings = get_settings()
    if not settings.close_api_key:
        raise CloseAPIError(0, "CLOSE_API_KEY ist nicht gesetzt")

    last_exc: Exception | None = None
    with _client() as client:
        for attempt in range(_MAX_RETRIES):
            try:
                resp = client.request(method, path, **kwargs)
            except httpx.TransportError as ex:
                last_exc = ex
                time.sleep(2**attempt)
                continue

            if resp.status_code < 300:
                return resp.json() if resp.content else {}

            if resp.status_code in _RETRY_STATUS and attempt < _MAX_RETRIES - 1:
                # Close liefert bei 429 "Retry-After" (Sekunden) - respektieren
                # statt blind zu verdoppeln, wenn vorhanden.
                wait = float(resp.headers.get("Retry-After", 2**attempt))
                time.sleep(wait)
                continue

            raise CloseAPIError(resp.status_code, resp.text[:500])

    raise CloseAPIError(0, str(last_exc) if last_exc else "unbekannter Transport-Fehler")


# ── Leads ─────────────────────────────────────────────────────────────────

def search_leads(query: str = "", limit: int = 25) -> list[dict]:
    params = {"_limit": limit}
    if query:
        params["query"] = query
    data = _request("GET", "/lead/", params=params)
    return data.get("data", [])


def get_lead(lead_id: str) -> dict:
    return _request("GET", f"/lead/{lead_id}/")


def create_lead(name: str, contacts: list[dict] | None = None, custom_fields: dict | None = None) -> dict:
    """contacts: Liste von {"name": ..., "emails": [{"email": ..., "type": "office"}]}.
    custom_fields: {"custom.<field_id>": wert} - siehe Settings.close_source_field_id."""
    payload: dict = {"name": name}
    if contacts:
        payload["contacts"] = contacts
    if custom_fields:
        payload.update(custom_fields)
    return _request("POST", "/lead/", json=payload)


def update_lead(lead_id: str, data: dict) -> dict:
    return _request("PUT", f"/lead/{lead_id}/", json=data)


def tag_lead_source(lead_id: str) -> dict:
    """Setzt das konfigurierte Quelle-Custom-Field auf close_source_value.
    No-op (gibt {} zurück) wenn kein close_source_field_id konfiguriert ist -
    Close-Custom-Fields müssen vorab in der UI/API angelegt werden, bevor eine
    ID existiert (siehe README.md)."""
    settings = get_settings()
    if not settings.close_source_field_id:
        return {}
    key = f"custom.{settings.close_source_field_id}"
    return update_lead(lead_id, {key: settings.close_source_value})


# ── Notes / Activities ───────────────────────────────────────────────────

def create_note(lead_id: str, text: str) -> dict:
    return _request("POST", "/activity/note/", json={"lead_id": lead_id, "note": text})


def list_activities(lead_id: str, limit: int = 25) -> list[dict]:
    data = _request("GET", "/activity/", params={"lead_id": lead_id, "_limit": limit})
    return data.get("data", [])


# ── Opportunities ─────────────────────────────────────────────────────────

def list_opportunities(lead_id: str) -> list[dict]:
    data = _request("GET", "/opportunity/", params={"lead_id": lead_id})
    return data.get("data", [])


# ── Custom Fields (Lead-Ebene) ───────────────────────────────────────────

def list_lead_custom_fields() -> list[dict]:
    data = _request("GET", "/custom_field/lead/")
    return data.get("data", [])
