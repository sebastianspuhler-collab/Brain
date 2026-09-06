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

# Close-Pagination (developer.close.com/topics/pagination/, live abgeglichen
# 2026-09-06): Offset-basiert über die Query-Parameter _skip/_limit, JEDE
# List-Response trägt "has_more" (bool). KEIN Cursor. Bugfix 2026-09-06:
# search_leads()/list_opportunities()/list_lead_custom_fields()/
# list_activities() haben bisher genau EINE Seite abgerufen und has_more nie
# geprüft - bei mehr Treffern als eine Seite (Close-Default bzw. der jeweils
# übergebene _limit-Wert) wurden alle weiteren Seiten still verworfen, ohne
# Fehler oder Warnung. _PAGE_SIZE=100 folgt dem offiziellen Doku-Beispiel
# (_skip=0&_limit=100, _skip=100&_limit=100, ...) - die Doku selbst nennt für
# _limit keinen festen Maximalwert.
_PAGE_SIZE = 100
# Notbremse gegen eine Endlosschleife, falls has_more fälschlich dauerhaft
# true bleibt oder der laut Doku "je nach Ressource unterschiedliche"
# _skip-Höchstwert erreicht wird (Close würde dann vermutlich einen 4xx-Fehler
# werfen, der ohnehin sofort durchgereicht wird, siehe _request) - kein
# Business in diesem Repo hat real 10.000+ Leads/Opportunities/Custom Fields.
_MAX_PAGES = 100


def _paginate(path: str, params: dict, max_results: int | None = None) -> list[dict]:
    """Blättert vollständig durch eine Close-List-Ressource, bis has_more
    False ist, eine leere Seite kommt, max_results erreicht ist, oder die
    _MAX_PAGES-Notbremse greift. max_results=None heißt "alles holen" (siehe
    list_opportunities/list_lead_custom_fields - dort gibt es semantisch
    keinen sinnvollen Teil-Cutoff)."""
    results: list[dict] = []
    skip = 0
    for _ in range(_MAX_PAGES):
        remaining = None if max_results is None else max_results - len(results)
        if remaining is not None and remaining <= 0:
            break
        page_params = dict(params)
        page_params["_limit"] = _PAGE_SIZE if remaining is None else min(_PAGE_SIZE, remaining)
        page_params["_skip"] = skip
        data = _request("GET", path, params=page_params)
        page_results = data.get("data", [])
        results.extend(page_results)
        if not page_results or not data.get("has_more"):
            break
        skip += len(page_results)
    return results


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
    """limit ist jetzt eine ECHTE Obergrenze über beliebig viele Seiten
    hinweg (siehe _paginate-Docstring), nicht mehr nur die _limit-Größe einer
    einzelnen Anfrage - vorher wurden Treffer jenseits der ersten Seite
    stillschweigend verworfen (Bugfix 2026-09-06)."""
    params: dict = {}
    if query:
        params["query"] = query
    return _paginate("/lead/", params, max_results=limit)


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
    """Bisherige Aufrufer nutzen hier ausschließlich kleine limit-Werte (10,
    1 - "die letzten N Activities"), sind also von der eigentlichen
    Pagination-Lücke nie betroffen gewesen. Trotzdem auf _paginate
    umgestellt (gleicher Bugfix 2026-09-06): identische Fehlerklasse, falls
    limit künftig größer als eine Close-Seite gesetzt wird."""
    return _paginate("/activity/", {"lead_id": lead_id}, max_results=limit)


# ── Opportunities ─────────────────────────────────────────────────────────

def list_opportunities(lead_id: str) -> list[dict]:
    """Kein limit-Parameter - hier ist "alle Opportunities dieses Leads" die
    einzig sinnvolle Semantik, siehe _paginate(max_results=None)."""
    return _paginate("/opportunity/", {"lead_id": lead_id}, max_results=None)


# ── Custom Fields (Lead-Ebene) ───────────────────────────────────────────

def list_lead_custom_fields() -> list[dict]:
    """Alle konfigurierten Lead-Custom-Field-Definitionen, kein Cutoff."""
    return _paginate("/custom_field/lead/", {}, max_results=None)
