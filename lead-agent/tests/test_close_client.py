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
