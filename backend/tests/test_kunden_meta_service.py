from app.services import kunden_meta_service as svc


def _use_tmp_agent_dir(tmp_path, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(
        type(get_settings()), "agent_dir", property(lambda self: tmp_path / "_agent"),
    )
    get_settings.cache_clear()


def test_get_meta_defaults_include_empty_overrides(tmp_path, monkeypatch):
    _use_tmp_agent_dir(tmp_path, monkeypatch)
    meta = svc.get_meta("Unbekannt")
    assert meta["overrides"] == {}


def test_upsert_meta_merges_overrides_without_dropping_existing(tmp_path, monkeypatch):
    _use_tmp_agent_dir(tmp_path, monkeypatch)
    svc.upsert_meta("Kunde", overrides={"anzeige_name": "Forlin GmbH"})
    ergebnis = svc.upsert_meta("Kunde", overrides={"aktueller_stand": "Wartet auf Rückmeldung"})
    assert ergebnis["overrides"] == {
        "anzeige_name": "Forlin GmbH",
        "aktueller_stand": "Wartet auf Rückmeldung",
    }


def test_upsert_meta_empty_string_removes_single_override_field(tmp_path, monkeypatch):
    _use_tmp_agent_dir(tmp_path, monkeypatch)
    svc.upsert_meta("Kunde", overrides={"anzeige_name": "Forlin GmbH", "aktueller_stand": "x"})
    ergebnis = svc.upsert_meta("Kunde", overrides={"aktueller_stand": ""})
    assert ergebnis["overrides"] == {"anzeige_name": "Forlin GmbH"}


def test_get_meta_backward_compatible_with_entries_missing_overrides_key(tmp_path, monkeypatch):
    _use_tmp_agent_dir(tmp_path, monkeypatch)
    # Simuliert einen vor der overrides-Erweiterung gespeicherten Eintrag.
    svc._save_all({"AltKunde": {"archiviert": False, "status_override": None, "notiz": "alt"}})
    meta = svc.get_meta("AltKunde")
    assert meta["overrides"] == {}
    assert meta["notiz"] == "alt"
