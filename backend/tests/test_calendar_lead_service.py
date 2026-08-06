import json

from app.services import calendar_lead_service as svc


class FakeSettings:
    def __init__(self, tmp_path):
        self.vault_path = tmp_path
        self.agent_dir = tmp_path / "_agent"


def _event(eid="evt-1", external_email="dominik@topdown-cf.com"):
    return {
        "id": eid,
        "subject": "Prozessia X TopDown",
        "attendees": [
            {"emailAddress": {"name": "Dominik", "address": external_email}},
        ],
        "start": {"dateTime": "2026-08-11T09:30:00"},
    }


def test_classify_event_returns_false_on_llm_exception(monkeypatch):
    def boom(*a, **k):
        raise TimeoutError("simulated LLM timeout")

    monkeypatch.setattr(svc, "complete_json", boom)
    result = svc._classify_event(_event(), [{"name": "Dominik", "address": "dominik@topdown-cf.com"}])
    assert result is False


def test_classify_event_returns_dict_for_a_valid_negative_answer(monkeypatch):
    monkeypatch.setattr(svc, "complete_json", lambda *a, **k: '{"ist_erstgespraech": false}')
    result = svc._classify_event(_event(), [{"name": "Dominik", "address": "dominik@topdown-cf.com"}])
    assert result == {"ist_erstgespraech": False}


def test_scan_for_new_leads_does_not_cache_a_failed_classification(tmp_path, monkeypatch):
    # Regressionstest für den TopDown-Bug (2026-08-06): ein Termin mit externem
    # Teilnehmer, dessen Klassifizierung fehlschlägt, darf NICHT dauerhaft als
    # "geprüft" gelten - sonst wird er nie wieder versucht.
    settings = FakeSettings(tmp_path)
    monkeypatch.setattr(svc, "get_settings", lambda: settings)
    monkeypatch.setattr(svc.outlook_client, "is_authenticated", lambda: True)
    monkeypatch.setattr(svc.outlook_client, "get_calendar_events", lambda days: [_event()])
    monkeypatch.setattr(svc.classify, "list_customer_names", lambda: [])
    monkeypatch.setattr(svc, "_classify_event", lambda event, external: False)

    found = svc.scan_for_new_leads()

    assert found == []
    cache_path = settings.agent_dir / "logs" / "calendar_lead_cache.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else []
    assert "evt-1" not in cache


def test_scan_for_new_leads_caches_a_successful_negative_classification(tmp_path, monkeypatch):
    settings = FakeSettings(tmp_path)
    monkeypatch.setattr(svc, "get_settings", lambda: settings)
    monkeypatch.setattr(svc.outlook_client, "is_authenticated", lambda: True)
    monkeypatch.setattr(svc.outlook_client, "get_calendar_events", lambda days: [_event()])
    monkeypatch.setattr(svc.classify, "list_customer_names", lambda: [])
    monkeypatch.setattr(svc, "_classify_event", lambda event, external: {"ist_erstgespraech": False})

    found = svc.scan_for_new_leads()

    assert found == []
    cache_path = settings.agent_dir / "logs" / "calendar_lead_cache.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    assert "evt-1" in cache


def test_scan_for_new_leads_creates_lead_stub_on_positive_classification(tmp_path, monkeypatch):
    settings = FakeSettings(tmp_path)
    monkeypatch.setattr(svc, "get_settings", lambda: settings)
    monkeypatch.setattr(svc.outlook_client, "is_authenticated", lambda: True)
    monkeypatch.setattr(svc.outlook_client, "get_calendar_events", lambda days: [_event()])
    monkeypatch.setattr(svc.classify, "list_customer_names", lambda: [])
    monkeypatch.setattr(svc.memory, "append_to_memory", lambda *a, **k: None)
    monkeypatch.setattr(
        svc, "_classify_event", lambda event, external: {"ist_erstgespraech": True, "firma": "TopDown"}
    )

    found = svc.scan_for_new_leads()

    assert found == ["TopDown"]
    leads = list((tmp_path / "Leads").glob("*TopDown*.md"))
    assert len(leads) == 1
    assert "topdown-cf.com" in leads[0].read_text(encoding="utf-8")
