from pathlib import Path

import close_client
import lead_lookup as svc
import vault_kunden
import vault_leads
from close_client import CloseAPIError


class FakeSettings:
    def __init__(self, tmp_path):
        self.vault_path = tmp_path

    @property
    def leads_dir(self) -> Path:
        return self.vault_path / "Leads"


def _patch_settings(monkeypatch, tmp_path):
    fake = FakeSettings(tmp_path)
    monkeypatch.setattr(vault_leads, "get_settings", lambda: fake)
    monkeypatch.setattr(vault_kunden, "get_settings", lambda: fake)
    return fake


def test_resolve_finds_vault_lead_and_linked_close_lead(tmp_path, monkeypatch):
    monkeypatch.setattr(vault_leads, "get_settings", lambda: FakeSettings(tmp_path))
    path = vault_leads.write_prospect("Verknuepfte Firma")
    vault_leads.update_fields(path, {"close_lead_id": "lead_abc"})
    monkeypatch.setattr(close_client, "get_lead", lambda lead_id: {"id": lead_id, "display_name": "Verknuepfte Firma"})

    resolved = svc.resolve("Verknuepfte")

    assert resolved["vault"] is not None
    assert resolved["close_lead_id"] == "lead_abc"
    assert resolved["close"]["display_name"] == "Verknuepfte Firma"


def test_resolve_by_close_lead_id_finds_vault_match(tmp_path, monkeypatch):
    monkeypatch.setattr(vault_leads, "get_settings", lambda: FakeSettings(tmp_path))
    path = vault_leads.write_prospect("Per Close ID")
    vault_leads.update_fields(path, {"close_lead_id": "lead_xyz"})
    monkeypatch.setattr(close_client, "get_lead", lambda lead_id: {"id": lead_id})

    resolved = svc.resolve("lead_xyz")

    assert resolved["vault"]["path"] == str(path)


def test_resolve_falls_back_to_close_search_when_nothing_local(tmp_path, monkeypatch):
    monkeypatch.setattr(vault_leads, "get_settings", lambda: FakeSettings(tmp_path))
    monkeypatch.setattr(
        close_client, "search_leads",
        lambda query, limit=1: [{"id": "lead_found", "display_name": "Nur In Close"}],
    )

    resolved = svc.resolve("Nur In Close")

    assert resolved["vault"] is None
    assert resolved["close_lead_id"] == "lead_found"
    assert resolved["close"]["display_name"] == "Nur In Close"


def test_resolve_returns_all_none_when_nothing_found(tmp_path, monkeypatch):
    _patch_settings(monkeypatch, tmp_path)
    monkeypatch.setattr(close_client, "search_leads", lambda query, limit=1: [])

    resolved = svc.resolve("Existiert Nicht")

    assert resolved == {"vault": None, "kunde": None, "close": None, "close_lead_id": None}


def test_resolve_handles_close_api_error_gracefully(tmp_path, monkeypatch):
    monkeypatch.setattr(vault_leads, "get_settings", lambda: FakeSettings(tmp_path))
    path = vault_leads.write_prospect("Close Ist Down")
    vault_leads.update_fields(path, {"close_lead_id": "lead_down"})

    def raise_error(lead_id):
        raise CloseAPIError(500, "down")

    monkeypatch.setattr(close_client, "get_lead", raise_error)

    resolved = svc.resolve("Close-Ist-Down")

    assert resolved["vault"] is not None
    assert resolved["close"] is None


def test_missing_core_fields_lists_only_unset_ones():
    resolved = {"vault": {"fields": {"branche": "Werkzeugbau", "groesse": "", "score": "5"}}}

    missing = svc.missing_core_fields(resolved)

    assert "branche" not in missing
    assert "groesse" in missing
    assert "produkt_leistung" in missing
    assert "zielgruppe" in missing


def test_missing_core_fields_all_missing_without_vault_lead():
    resolved = {"vault": None}

    missing = svc.missing_core_fields(resolved)

    assert set(missing) == set(svc.CORE_FIELDS)


def test_resolve_finds_kunde_folder_without_close_link(tmp_path, monkeypatch):
    _patch_settings(monkeypatch, tmp_path)
    (tmp_path / "Kunden" / "F-Tronic").mkdir(parents=True)

    resolved = svc.resolve("F-Tronic")

    assert resolved["kunde"] is not None
    assert resolved["kunde"]["firma"] == "F-Tronic"
    assert resolved["vault"] is None
    assert resolved["close_lead_id"] is None
    assert resolved["close"] is None


def test_resolve_finds_kunde_and_its_linked_close_lead(tmp_path, monkeypatch):
    _patch_settings(monkeypatch, tmp_path)
    kunde_path = tmp_path / "Kunden" / "F-Tronic"
    kunde_path.mkdir(parents=True)
    vault_kunden.link_to_close(kunde_path, "lead_ft")
    monkeypatch.setattr(close_client, "get_lead", lambda lead_id: {"id": lead_id, "display_name": "F-Tronic"})

    resolved = svc.resolve("F-Tronic")

    assert resolved["kunde"]["close_lead_id"] == "lead_ft"
    assert resolved["close_lead_id"] == "lead_ft"
    assert resolved["close"]["display_name"] == "F-Tronic"


def test_resolve_prefers_lead_over_kunde_when_both_exist(tmp_path, monkeypatch):
    _patch_settings(monkeypatch, tmp_path)
    (tmp_path / "Kunden" / "Doppelgaenger").mkdir(parents=True)
    path = vault_leads.write_prospect("Doppelgaenger")
    vault_leads.update_fields(path, {"close_lead_id": "lead_from_leads_md"})
    monkeypatch.setattr(close_client, "get_lead", lambda lead_id: {"id": lead_id})

    resolved = svc.resolve("Doppelgaenger")

    assert resolved["vault"] is not None
    assert resolved["close_lead_id"] == "lead_from_leads_md"
