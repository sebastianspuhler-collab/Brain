import vault_kunden as svc


class FakeSettings:
    def __init__(self, tmp_path):
        self.vault_path = tmp_path


def _make_kunde(tmp_path, name):
    d = tmp_path / "Kunden" / name
    d.mkdir(parents=True)
    return d


def test_list_kunden_returns_folder_names_without_close_link(tmp_path, monkeypatch):
    monkeypatch.setattr(svc, "get_settings", lambda: FakeSettings(tmp_path))
    _make_kunde(tmp_path, "F-Tronic")
    _make_kunde(tmp_path, "Schaufler")

    kunden = svc.list_kunden()

    names = {k["firma"] for k in kunden}
    assert names == {"F-Tronic", "Schaufler"}
    assert all(k["close_lead_id"] == "" for k in kunden)


def test_list_kunden_excludes_vorlage_and_dotfolders(tmp_path, monkeypatch):
    monkeypatch.setattr(svc, "get_settings", lambda: FakeSettings(tmp_path))
    _make_kunde(tmp_path, "_Vorlage")
    _make_kunde(tmp_path, ".obsidian")
    _make_kunde(tmp_path, "Echtefirma")

    kunden = svc.list_kunden()

    assert [k["firma"] for k in kunden] == ["Echtefirma"]


def test_list_kunden_returns_empty_list_when_kunden_dir_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(svc, "get_settings", lambda: FakeSettings(tmp_path))

    assert svc.list_kunden() == []


def test_link_to_close_then_read_back(tmp_path, monkeypatch):
    monkeypatch.setattr(svc, "get_settings", lambda: FakeSettings(tmp_path))
    kunde_path = _make_kunde(tmp_path, "F-Tronic")

    svc.link_to_close(kunde_path, "lead_abc123")

    assert svc.read_close_lead_id(kunde_path) == "lead_abc123"
    kunden = svc.list_kunden()
    assert kunden[0]["close_lead_id"] == "lead_abc123"


def test_find_kunde_exact_path(tmp_path, monkeypatch):
    monkeypatch.setattr(svc, "get_settings", lambda: FakeSettings(tmp_path))
    _make_kunde(tmp_path, "F-Tronic")

    found = svc.find_kunde("Kunden/F-Tronic")

    assert found is not None
    assert found["firma"] == "F-Tronic"


def test_find_kunde_by_keyword(tmp_path, monkeypatch):
    monkeypatch.setattr(svc, "get_settings", lambda: FakeSettings(tmp_path))
    _make_kunde(tmp_path, "Schmidt-Haensch")

    found = svc.find_kunde("schmidt")

    assert found is not None
    assert found["firma"] == "Schmidt-Haensch"


def test_find_kunde_returns_none_for_vorlage(tmp_path, monkeypatch):
    monkeypatch.setattr(svc, "get_settings", lambda: FakeSettings(tmp_path))
    _make_kunde(tmp_path, "_Vorlage")

    assert svc.find_kunde("_Vorlage") is None


def test_find_kunde_returns_none_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(svc, "get_settings", lambda: FakeSettings(tmp_path))

    assert svc.find_kunde("Existiert Nicht") is None
