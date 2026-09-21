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
import json
import tempfile
import time
from pathlib import Path

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

# Voll-Snapshot aller Close-Leads auf Platte (Stand 2026-09-21: ~1900 Leads,
# ein Voll-Abruf dauert ~30 s). Jeder claude -p-Aufruf startet einen frischen
# MCP-Prozess, ein reiner In-Memory-Cache würde also nie greifen. NUR für
# Listen-/Filterabfragen (combined_leads) gedacht - Dublettenprüfung und alle
# Schreibpfade fragen immer live bei Close nach (find_lead_candidates).
# Jede eigene Schreiboperation verwirft den Snapshot (invalidate_snapshot).
SNAPSHOT_PATH = Path(tempfile.gettempdir()) / "lead_agent_close_snapshot.json"
SNAPSHOT_MAX_AGE_SECONDS = 300


def invalidate_snapshot() -> None:
    try:
        SNAPSHOT_PATH.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass


def _read_snapshot(max_age: float) -> list[dict] | None:
    try:
        if time.time() - SNAPSHOT_PATH.stat().st_mtime > max_age:
            return None
        return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write_snapshot(leads: list[dict]) -> None:
    try:
        tmp = SNAPSHOT_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(leads), encoding="utf-8")
        tmp.replace(SNAPSHOT_PATH)
    except OSError:
        pass


def search_leads(query: str = "", limit: int = 25, cached: bool = False) -> list[dict]:
    """limit ist eine ECHTE Obergrenze über beliebig viele Seiten hinweg (siehe
    _paginate-Docstring). cached=True: nur für die leere Query (= alle Leads)
    erlaubt, liefert den Platten-Snapshot, falls jünger als
    SNAPSHOT_MAX_AGE_SECONDS, sonst frisch holen und Snapshot neu schreiben.
    Ein Snapshot wird nur gespeichert, wenn er nicht durch limit gekappt
    wurde, sonst würde ein späterer Aufruf mit größerem limit unvollständige
    Daten bekommen."""
    if cached and not query:
        snap = _read_snapshot(SNAPSHOT_MAX_AGE_SECONDS)
        if snap is not None and len(snap) <= limit:
            return snap
        leads = _paginate("/lead/", {}, max_results=limit)
        if len(leads) < limit:
            _write_snapshot(leads)
        return leads
    params: dict = {}
    if query:
        params["query"] = query
    return _paginate("/lead/", params, max_results=limit)


def get_lead(lead_id: str) -> dict:
    return _request("GET", f"/lead/{lead_id}/")


def create_lead(name: str, contacts: list[dict] | None = None, custom_fields: dict | None = None, extra: dict | None = None) -> dict:
    """contacts: Liste von {"name": ..., "emails": [{"email": ..., "type": "office"}]}.
    custom_fields: {"custom.<field_id>": wert} - siehe custom_field_ids().
    extra: weitere native Close-Felder (url, addresses, description)."""
    payload: dict = {"name": name}
    if contacts:
        payload["contacts"] = contacts
    if custom_fields:
        payload.update(custom_fields)
    if extra:
        payload.update(extra)
    result = _request("POST", "/lead/", json=payload)
    invalidate_snapshot()
    return result


def update_lead(lead_id: str, data: dict) -> dict:
    result = _request("PUT", f"/lead/{lead_id}/", json=data)
    invalidate_snapshot()
    return result


def tag_lead_source(lead_id: str) -> dict:
    """Setzt das konfigurierte Quelle-Custom-Field auf close_source_value.
    No-op (gibt {} zurück) wenn kein close_source_field_id konfiguriert ist -
    Close-Custom-Fields müssen vorab in der UI/API angelegt werden, bevor eine
    ID existiert (siehe README.md). Stand 2026-09-21: in diesem Close-Account
    existiert kein "Quelle"-Feld, der Aufruf ist also aktuell wirkungslos -
    save_prospect schreibt die Herkunft deshalb zusätzlich in die erste Note."""
    settings = get_settings()
    if not settings.close_source_field_id:
        return {}
    key = f"custom.{settings.close_source_field_id}"
    return update_lead(lead_id, {key: settings.close_source_value})


def find_lead_candidates(name_queries: list[str]) -> list[dict]:
    """LIVE-Suche (kein Snapshot) nach mehreren Stichworten (Firmenname,
    Domain, ...) - Vereinigung ohne Dubletten, für die Dublettenprüfung vor
    dem Anlegen. Ein einzelner Suchfehler bricht nicht ab, wird aber
    weitergereicht, wenn ALLE Anfragen fehlschlagen (dann wäre "keine
    Treffer" eine gefährliche Fehlinformation)."""
    found: dict[str, dict] = {}
    errors: list[CloseAPIError] = []
    tried = 0
    for q in name_queries:
        q = (q or "").strip()
        if not q:
            continue
        tried += 1
        try:
            for lead in search_leads(q, limit=50):
                if lead.get("id"):
                    found.setdefault(lead["id"], lead)
        except CloseAPIError as e:
            errors.append(e)
    if tried and len(errors) == tried:
        raise errors[0]
    return list(found.values())


# ── Lead-Status / Custom-Field-Auflösung ─────────────────────────────────

def list_lead_statuses() -> list[dict]:
    """Konfigurierte Lead-Status ({id, label}) - Close erlaubt beim Setzen nur
    diese, der Agent legt keine neuen an."""
    return _request("GET", "/status/lead/").get("data", [])


def status_id_for(label: str) -> str | None:
    wanted = (label or "").strip().lower()
    for st in list_lead_statuses():
        if (st.get("label") or "").strip().lower() == wanted:
            return st.get("id")
    return None


def custom_field_ids() -> dict[str, dict]:
    """{Feldname (klein): {"id": ..., "type": ...}} der Lead-Custom-Fields.
    Close liefert an Leads die Werte unter dem Feld-NAMEN (lead["custom"]),
    schreibt aber nur über custom.<field_id> - diese Zuordnung hier."""
    return {
        (f.get("name") or "").strip().lower(): {"id": f["id"], "type": f.get("type", "text"), "name": f.get("name")}
        for f in list_lead_custom_fields() if f.get("id")
    }


# ── Contacts ─────────────────────────────────────────────────────────────

def create_contact(lead_id: str, name: str, title: str = "", emails: list[str] | None = None, phones: list[str] | None = None) -> dict:
    payload: dict = {"lead_id": lead_id}
    if name:
        payload["name"] = name
    if title:
        payload["title"] = title
    if emails:
        payload["emails"] = [{"email": e, "type": "office"} for e in emails]
    if phones:
        payload["phones"] = [{"phone": ph, "type": "office"} for ph in phones]
    result = _request("POST", "/contact/", json=payload)
    invalidate_snapshot()
    return result


def update_contact(contact_id: str, data: dict) -> dict:
    result = _request("PUT", f"/contact/{contact_id}/", json=data)
    invalidate_snapshot()
    return result


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
