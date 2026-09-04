from pathlib import Path

import vault_leads as svc


class FakeSettings:
    def __init__(self, tmp_path):
        self.vault_path = tmp_path

    @property
    def leads_dir(self) -> Path:
        return self.vault_path / "Leads"


def test_write_prospect_creates_expected_frontmatter(tmp_path, monkeypatch):
    monkeypatch.setattr(svc, "get_settings", lambda: FakeSettings(tmp_path))

    path = svc.write_prospect("Muster GmbH", kontakt_name="Max Muster", kontakt_email="max@muster.de", notiz="Passt zum ICP.", quelle="Recherche")

    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "kategorie: Lead" in text
    assert "status: neu" in text
    assert "close_lead_id:" in text
    assert "max@muster.de" in text
    assert "# Muster GmbH" in text


def test_update_fields_patches_only_requested_keys_and_preserves_tags_block(tmp_path, monkeypatch):
    monkeypatch.setattr(svc, "get_settings", lambda: FakeSettings(tmp_path))
    path = svc.write_prospect("Beispiel AG")
    original = path.read_text(encoding="utf-8")
    assert "tags:\n  - Lead\n  - Lead-Agent-Recherche" in original

    svc.update_fields(path, {"close_lead_id": "lead_abc123", "status": "kontaktiert"})

    updated = path.read_text(encoding="utf-8")
    assert "close_lead_id: lead_abc123" in updated
    assert "status: kontaktiert" in updated
    # Der mehrzeilige tags-Block darf durch das Zeilen-Patching nicht
    # verloren gehen (siehe update_fields-Docstring: Regression-Schutz).
    assert "tags:\n  - Lead\n  - Lead-Agent-Recherche" in updated


def test_find_lead_matches_by_filename_keyword(tmp_path, monkeypatch):
    monkeypatch.setattr(svc, "get_settings", lambda: FakeSettings(tmp_path))
    svc.write_prospect("Sonderfall Elektrotechnik GmbH")

    found = svc.find_lead("Sonderfall")

    assert found is not None
    assert "Sonderfall" in found["filename"]


def test_find_lead_by_close_id(tmp_path, monkeypatch):
    monkeypatch.setattr(svc, "get_settings", lambda: FakeSettings(tmp_path))
    path = svc.write_prospect("Andere Firma")
    svc.update_fields(path, {"close_lead_id": "lead_xyz"})

    found = svc.find_lead_by_close_id("lead_xyz")

    assert found is not None
    assert found["path"] == str(path)
    assert svc.find_lead_by_close_id("does-not-exist") is None


def test_list_leads_excludes_archived_entries(tmp_path, monkeypatch):
    monkeypatch.setattr(svc, "get_settings", lambda: FakeSettings(tmp_path))
    svc.write_prospect("Aktiver Lead")
    archived = svc.leads_dir() / "2026-01-01-Archiviert.md"
    archived.write_text("---\nkategorie: Archiv\n---\n\n# Archiviert\n", encoding="utf-8")

    leads = svc.list_leads()

    names = [lead["filename"] for lead in leads]
    assert any("Aktiver-Lead" in n for n in names)
    assert not any("Archiviert" in n for n in names)
