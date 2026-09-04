import hashlib
import hmac
import time
from pathlib import Path

import pytest

import vault_leads
import webhooks as svc


class FakeSettings:
    close_webhook_signing_key = "test-signing-key"

    def __init__(self, tmp_path=None):
        self.vault_path = tmp_path

    @property
    def leads_dir(self):
        return self.vault_path / "Leads"


def _sign(key: str, timestamp: str, body: bytes) -> str:
    return hmac.new(key.encode(), timestamp.encode() + body, hashlib.sha256).hexdigest()


def test_verify_signature_accepts_valid_hmac(monkeypatch):
    monkeypatch.setattr(svc, "get_settings", lambda: FakeSettings())
    body = b'{"type": "lead.updated"}'
    ts = str(int(time.time()))
    sig = _sign("test-signing-key", ts, body)

    svc.verify_signature(body, ts, sig)  # muss ohne Exception durchlaufen


def test_verify_signature_rejects_wrong_hash(monkeypatch):
    monkeypatch.setattr(svc, "get_settings", lambda: FakeSettings())
    body = b'{"type": "lead.updated"}'
    ts = str(int(time.time()))

    with pytest.raises(svc.WebhookAuthError):
        svc.verify_signature(body, ts, "deadbeef")


def test_verify_signature_rejects_stale_timestamp(monkeypatch):
    monkeypatch.setattr(svc, "get_settings", lambda: FakeSettings())
    body = b'{"type": "lead.updated"}'
    ts = str(int(time.time()) - 3600)
    sig = _sign("test-signing-key", ts, body)

    with pytest.raises(svc.WebhookAuthError):
        svc.verify_signature(body, ts, sig)


def test_verify_signature_fails_closed_without_configured_secret(monkeypatch):
    class NoSecretSettings(FakeSettings):
        close_webhook_signing_key = ""

    monkeypatch.setattr(svc, "get_settings", lambda: NoSecretSettings())
    with pytest.raises(svc.WebhookAuthError):
        svc.verify_signature(b"{}", str(int(time.time())), "irrelevant")


def test_handle_payload_updates_matching_vault_lead_status(tmp_path, monkeypatch):
    fake = FakeSettings(tmp_path)
    monkeypatch.setattr(vault_leads, "get_settings", lambda: fake)
    monkeypatch.setattr(svc, "get_settings", lambda: fake)

    path = vault_leads.write_prospect("Kontakt GmbH")
    vault_leads.update_fields(path, {"close_lead_id": "lead_42"})

    result = svc.handle_payload({"type": "activity.call.created", "lead_id": "lead_42"})

    assert result["results"][0]["handled"] is True
    assert result["results"][0]["new_status"] == "kontaktiert"
    assert "status: kontaktiert" in Path(path).read_text(encoding="utf-8")


def test_handle_payload_reports_unhandled_when_no_matching_lead(tmp_path, monkeypatch):
    fake = FakeSettings(tmp_path)
    monkeypatch.setattr(vault_leads, "get_settings", lambda: fake)
    monkeypatch.setattr(svc, "get_settings", lambda: fake)

    result = svc.handle_payload({"type": "activity.call.created", "lead_id": "lead_unbekannt"})

    assert result["results"][0]["handled"] is False


def test_handle_payload_maps_opportunity_won(tmp_path, monkeypatch):
    fake = FakeSettings(tmp_path)
    monkeypatch.setattr(vault_leads, "get_settings", lambda: fake)
    monkeypatch.setattr(svc, "get_settings", lambda: fake)

    path = vault_leads.write_prospect("Gewonnene Firma")
    vault_leads.update_fields(path, {"close_lead_id": "lead_won"})

    result = svc.handle_payload({
        "type": "opportunity.status_updated",
        "lead_id": "lead_won",
        "data": {"status_type": "won"},
    })

    assert result["results"][0]["new_status"] == "gewonnen"
