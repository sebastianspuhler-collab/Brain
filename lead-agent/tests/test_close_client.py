import httpx
import pytest

import close_client as svc


class FakeSettings:
    close_api_key = "test-key"
    close_api_base = "https://api.close.com/api/v1"
    close_source_field_id = ""
    close_source_value = "prozessia-lead-agent"


def test_request_without_api_key_raises_immediately(monkeypatch):
    class NoKeySettings(FakeSettings):
        close_api_key = ""

    monkeypatch.setattr(svc, "get_settings", lambda: NoKeySettings())
    with pytest.raises(svc.CloseAPIError):
        svc.search_leads()


def test_request_retries_on_429_then_succeeds(monkeypatch):
    monkeypatch.setattr(svc, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(svc.time, "sleep", lambda *_: None)

    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "0"}, text="rate limited")
        return httpx.Response(200, json={"data": [{"id": "lead_1"}]})

    monkeypatch.setattr(svc, "_client", lambda: httpx.Client(base_url=FakeSettings.close_api_base, transport=httpx.MockTransport(handler)))

    result = svc.search_leads("Muster")

    assert calls["n"] == 2
    assert result == [{"id": "lead_1"}]


def test_request_raises_on_permanent_4xx_without_retry(monkeypatch):
    monkeypatch.setattr(svc, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(svc.time, "sleep", lambda *_: None)

    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(404, text="not found")

    monkeypatch.setattr(svc, "_client", lambda: httpx.Client(base_url=FakeSettings.close_api_base, transport=httpx.MockTransport(handler)))

    with pytest.raises(svc.CloseAPIError) as exc_info:
        svc.get_lead("lead_missing")

    assert calls["n"] == 1
    assert exc_info.value.status_code == 404


def test_tag_lead_source_is_noop_without_configured_field(monkeypatch):
    monkeypatch.setattr(svc, "get_settings", lambda: FakeSettings())
    called = {}
    monkeypatch.setattr(svc, "update_lead", lambda *a, **k: called.setdefault("hit", True))

    result = svc.tag_lead_source("lead_1")

    assert result == {}
    assert "hit" not in called


# ── Pagination (Bugfix 2026-09-06) ──────────────────────────────────────────
# Vorher: search_leads()/list_opportunities()/list_lead_custom_fields()/
# list_activities() haben genau EINE Close-Seite abgerufen und "has_more" nie
# geprüft - Treffer jenseits der ersten Seite wurden still verworfen.

def _paged_handler(items: list[dict], calls: list):
    """Simuliert einen Close-List-Endpoint über einer FLACHEN Liste von
    items - liest _skip/_limit aus der Anfrage und schneidet items[skip:skip+
    limit] heraus, has_more korrekt danach ob noch etwas übrig ist. Exakt das
    Schema aus developer.close.com/topics/pagination/ (_skip=0&_limit=100,
    _skip=100&_limit=100, ..., has_more zeigt das Ende an)."""
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(dict(request.url.params))
        skip = int(request.url.params.get("_skip", "0"))
        page_size = int(request.url.params.get("_limit", "100"))
        page = items[skip:skip + page_size]
        has_more = (skip + len(page)) < len(items)
        return httpx.Response(200, json={"data": page, "has_more": has_more})
    return handler


def test_search_leads_paginates_through_all_pages(monkeypatch):
    monkeypatch.setattr(svc, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(svc.time, "sleep", lambda *_: None)

    items = [{"id": f"lead_{i}"} for i in range(300)]
    calls: list = []
    monkeypatch.setattr(
        svc, "_client",
        lambda: httpx.Client(base_url=FakeSettings.close_api_base, transport=httpx.MockTransport(_paged_handler(items, calls))),
    )

    result = svc.search_leads(limit=1000)

    assert len(result) == 300
    assert result[0]["id"] == "lead_0"
    assert result[-1]["id"] == "lead_299"
    # Drei Seiten -> drei Requests, mit korrekt inkrementierendem _skip.
    assert [c["_skip"] for c in calls] == ["0", "100", "200"]


def test_search_leads_stops_exactly_at_requested_limit_even_with_more_pages(monkeypatch):
    monkeypatch.setattr(svc, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(svc.time, "sleep", lambda *_: None)

    items = [{"id": f"lead_{i}"} for i in range(300)]
    calls: list = []
    monkeypatch.setattr(
        svc, "_client",
        lambda: httpx.Client(base_url=FakeSettings.close_api_base, transport=httpx.MockTransport(_paged_handler(items, calls))),
    )

    result = svc.search_leads(limit=150)

    assert len(result) == 150
    assert len(calls) == 2
    # Zweite Anfrage darf nur noch die restlichen 50 anfordern, nicht 100.
    assert calls[1]["_limit"] == "50"


def test_search_leads_stops_on_empty_page_even_if_has_more_true(monkeypatch):
    monkeypatch.setattr(svc, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(svc.time, "sleep", lambda *_: None)

    def handler(request: httpx.Request) -> httpx.Response:
        # Defensive Absicherung gegen eine kaputte/inkonsistente API-Antwort:
        # has_more=True aber leere data -> darf keine Endlosschleife auslösen.
        return httpx.Response(200, json={"data": [], "has_more": True})

    monkeypatch.setattr(
        svc, "_client",
        lambda: httpx.Client(base_url=FakeSettings.close_api_base, transport=httpx.MockTransport(handler)),
    )

    result = svc.search_leads(limit=1000)

    assert result == []


def test_list_opportunities_fetches_all_pages_without_explicit_limit(monkeypatch):
    monkeypatch.setattr(svc, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(svc.time, "sleep", lambda *_: None)

    items = [{"id": f"opp_{i}"} for i in range(200)]
    calls: list = []
    monkeypatch.setattr(
        svc, "_client",
        lambda: httpx.Client(base_url=FakeSettings.close_api_base, transport=httpx.MockTransport(_paged_handler(items, calls))),
    )

    result = svc.list_opportunities("lead_1")

    assert len(result) == 200
    assert all(c.get("lead_id") == "lead_1" for c in calls)


def test_paginate_respects_max_pages_safety_net(monkeypatch):
    monkeypatch.setattr(svc, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(svc.time, "sleep", lambda *_: None)
    monkeypatch.setattr(svc, "_MAX_PAGES", 3)

    def always_more(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"id": "x"}] * 100, "has_more": True})

    monkeypatch.setattr(
        svc, "_client",
        lambda: httpx.Client(base_url=FakeSettings.close_api_base, transport=httpx.MockTransport(always_more)),
    )

    result = svc.search_leads(limit=1_000_000)

    # Bricht nach _MAX_PAGES Seiten ab statt endlos weiterzublättern.
    assert len(result) == 300
