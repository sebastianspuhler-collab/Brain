from pathlib import Path

import close_audit as svc
import close_client
import vault_kunden
import vault_leads
from close_client import CloseAPIError


class FakeSettings:
    def __init__(self, tmp_path):
        self.vault_path = tmp_path

    @property
    def leads_dir(self) -> Path:
        return self.vault_path / "Leads"


def _make_kunde(tmp_path, name):
    d = tmp_path / "Kunden" / name
    d.mkdir(parents=True)
    return d


def _patch_settings(monkeypatch, tmp_path):
    fake = FakeSettings(tmp_path)
    monkeypatch.setattr(vault_kunden, "get_settings", lambda: fake)
    monkeypatch.setattr(vault_leads, "get_settings", lambda: fake)
    return fake


def test_audit_finds_kunde_matching_close_lead_by_name(tmp_path, monkeypatch):
    _patch_settings(monkeypatch, tmp_path)
    _make_kunde(tmp_path, "F-Tronic")
    monkeypatch.setattr(
        close_client, "search_leads",
        lambda query, limit=5000: [{"id": "lead_ft", "display_name": "f-tronic GmbH"}],
    )

    result = svc.audit()

    assert result["ok"] is True
    assert len(result["neu_verknuepfbar"]) == 1
    match = result["neu_verknuepfbar"][0]
    assert match["firma"] == "F-Tronic"
    assert match["typ"] == "kunde"
    assert match["close_lead_id"] == "lead_ft"
    assert result["kunden_ohne_close_kontakt"] == []


def test_audit_reports_kunde_without_any_close_match(tmp_path, monkeypatch):
    _patch_settings(monkeypatch, tmp_path)
    _make_kunde(tmp_path, "Ganz Neue Firma")
    monkeypatch.setattr(close_client, "search_leads", lambda query, limit=5000: [])

    result = svc.audit()

    assert result["neu_verknuepfbar"] == []
    assert [k["firma"] for k in result["kunden_ohne_close_kontakt"]] == ["Ganz Neue Firma"]


def test_audit_skips_kunde_already_linked(tmp_path, monkeypatch):
    _patch_settings(monkeypatch, tmp_path)
    kunde_path = _make_kunde(tmp_path, "Schon Verknuepft")
    vault_kunden.link_to_close(kunde_path, "lead_existing")
    monkeypatch.setattr(
        close_client, "search_leads",
        lambda query, limit=5000: [{"id": "lead_existing", "display_name": "Schon Verknuepft"}],
    )

    result = svc.audit()

    assert result["bereits_verknuepft"] == 1
    assert result["neu_verknuepfbar"] == []


def test_audit_covers_leads_ohne_close_kontakt_too(tmp_path, monkeypatch):
    _patch_settings(monkeypatch, tmp_path)
    vault_leads.write_prospect("Frischer Lead Ohne Close")
    monkeypatch.setattr(close_client, "search_leads", lambda query, limit=5000: [])

    result = svc.audit()

    assert [x["firma"] for x in result["leads_ohne_close_kontakt"]] == ["Frischer-Lead-Ohne-Close"]


def test_audit_caps_unmatched_close_preview_but_reports_full_count(tmp_path, monkeypatch):
    _patch_settings(monkeypatch, tmp_path)
    close_leads = [{"id": f"lead_{i}", "display_name": f"Firma {i}"} for i in range(50)]
    monkeypatch.setattr(close_client, "search_leads", lambda query, limit=5000: close_leads)

    result = svc.audit()

    assert result["close_leads_gesamt"] == 50
    assert result["close_leads_ohne_vault_treffer_anzahl"] == 50
    assert len(result["close_leads_ohne_vault_treffer_beispiele"]) == svc._MAX_UNMATCHED_CLOSE_PREVIEW


def test_audit_returns_error_on_close_failure(tmp_path, monkeypatch):
    _patch_settings(monkeypatch, tmp_path)

    def raise_error(query, limit=5000):
        raise CloseAPIError(500, "down")

    monkeypatch.setattr(close_client, "search_leads", raise_error)

    result = svc.audit()

    assert result["ok"] is False
    assert "error" in result


def test_link_writes_to_kunde_folder(tmp_path, monkeypatch):
    _patch_settings(monkeypatch, tmp_path)
    _make_kunde(tmp_path, "F-Tronic")

    result = svc.link("F-Tronic", "lead_new")

    assert result["ok"] is True
    assert result["typ"] == "kunde"
    assert vault_kunden.read_close_lead_id(tmp_path / "Kunden" / "F-Tronic") == "lead_new"


def test_link_writes_to_lead_frontmatter(tmp_path, monkeypatch):
    _patch_settings(monkeypatch, tmp_path)
    path = vault_leads.write_prospect("Ein Lead")

    result = svc.link("Ein-Lead", "lead_new")

    assert result["ok"] is True
    assert result["typ"] == "lead"
    assert "close_lead_id: lead_new" in Path(path).read_text(encoding="utf-8")


def test_link_returns_error_when_nothing_found(tmp_path, monkeypatch):
    _patch_settings(monkeypatch, tmp_path)

    result = svc.link("Existiert Nicht", "lead_x")

    assert result["ok"] is False
