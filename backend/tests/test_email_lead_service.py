import json

from app.services import email_indexer, email_lead_service as svc


class FakeSettings:
    def __init__(self, tmp_path):
        self.vault_path = tmp_path
        self.agent_dir = tmp_path / "_agent"


def test_looks_automated_matches_common_system_senders():
    assert svc._looks_automated("Newsletter <newsletter@foo.de>")
    assert svc._looks_automated("noreply@bar.com")
    assert not svc._looks_automated("dominik.nussbaumer@topdown-cf.com")


def test_classify_email_returns_false_on_llm_exception(monkeypatch):
    def boom(*a, **k):
        raise TimeoutError("simulated LLM timeout")

    monkeypatch.setattr(svc, "complete_json", boom)
    assert svc._classify_email("a@b.de", "Betreff", "Text") is False


def test_consider_new_lead_does_not_cache_a_failed_classification(tmp_path, monkeypatch):
    settings = FakeSettings(tmp_path)
    monkeypatch.setattr(svc, "get_settings", lambda: settings)
    monkeypatch.setattr(svc, "_classify_email", lambda sender, subject, body: False)

    result = svc.consider_new_lead("mail-1", "dominik@topdown-cf.com", "Anfrage", "Mon, 13 Jul 2026 14:59:32 +0000", "Text")

    assert result is None
    cache_path = settings.agent_dir / "logs" / "email_lead_cache.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else []
    assert "mail-1" not in cache


def test_consider_new_lead_skips_known_customer_names(tmp_path, monkeypatch):
    settings = FakeSettings(tmp_path)
    monkeypatch.setattr(svc, "get_settings", lambda: settings)
    monkeypatch.setattr(svc.classify, "list_customer_names", lambda: ["TopDown"])
    monkeypatch.setattr(svc.classify, "list_lead_names", lambda: [])
    monkeypatch.setattr(
        svc, "_classify_email", lambda sender, subject, body: {"ist_geschaeftsanfrage": True, "firma": "TopDown GmbH"}
    )

    result = svc.consider_new_lead("mail-1", "dominik@topdown-cf.com", "Anfrage", "Mon, 13 Jul 2026 14:59:32 +0000", "Text")

    assert result is None
    assert not (tmp_path / "Leads").exists()


def test_consider_new_lead_writes_stub_and_correspondence_for_a_genuine_new_contact(tmp_path, monkeypatch):
    settings = FakeSettings(tmp_path)
    monkeypatch.setattr(svc, "get_settings", lambda: settings)
    # _write_lead_correspondence() lebt in email_indexer.py und liest dort
    # eine eigene get_settings()-Bindung - separat patchen, sonst schreibt der
    # Korrespondenz-Teil am FakeSettings-Vault vorbei in die echten Settings.
    monkeypatch.setattr(email_indexer, "get_settings", lambda: settings)
    monkeypatch.setattr(svc.classify, "list_customer_names", lambda: [])
    monkeypatch.setattr(svc.classify, "list_lead_names", lambda: [])
    monkeypatch.setattr(svc.memory, "append_to_memory", lambda *a, **k: None)
    monkeypatch.setattr(
        svc, "_classify_email", lambda sender, subject, body: {"ist_geschaeftsanfrage": True, "firma": "TopDown"}
    )

    result = svc.consider_new_lead(
        "mail-1", "dominik.nussbaumer@topdown-cf.com", "Anfrage KI-Beratung",
        "Mon, 13 Jul 2026 14:59:32 +0000", "Wir suchen Unterstuetzung bei einem KI-Projekt.",
    )

    assert result == "TopDown"
    stubs = list((tmp_path / "Leads").glob("*TopDown*.md"))
    assert len(stubs) == 1
    assert "dominik.nussbaumer@topdown-cf.com" in stubs[0].read_text(encoding="utf-8")

    korr_dir = tmp_path / "Leads" / "TopDown-Korrespondenz"
    korr_dateien = list(korr_dir.glob("*.md"))
    assert len(korr_dateien) == 1
    assert "lead: TopDown" in korr_dateien[0].read_text(encoding="utf-8")

    cache_path = settings.agent_dir / "logs" / "email_lead_cache.json"
    assert "mail-1" in json.loads(cache_path.read_text(encoding="utf-8"))
