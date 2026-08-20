from app.services import vault_service as svc


class _FakeSettings:
    def __init__(self, tmp_path):
        self.vault_path = tmp_path


def _fake(tmp_path, monkeypatch):
    settings = _FakeSettings(tmp_path)
    monkeypatch.setattr(svc, "get_settings", lambda: settings)
    monkeypatch.setattr(svc.rag, "is_loaded", lambda: False)
    return settings


# ── Soft-Delete / Papierkorb (2026-08-20) ───────────────────────────────────
# Hintergrund: vault_delete() loeschte vorher echt (shutil.rmtree/unlink),
# obwohl das die CLAUDE.md-Regel "Dateien niemals loeschen ohne explizite
# Bestaetigung" bereits verletzte - jetzt Soft-Delete nach _agent/trash/.

def test_vault_delete_moves_file_to_trash_preserving_relative_path(tmp_path, monkeypatch):
    settings = _fake(tmp_path, monkeypatch)
    kunde_dir = tmp_path / "Kunden" / "TestKunde"
    kunde_dir.mkdir(parents=True)
    f = kunde_dir / "Angebot.pdf"
    f.write_text("Inhalt")

    result = svc.vault_delete("Kunden/TestKunde/Angebot.pdf")

    assert result["ok"] is True
    assert not f.exists()
    trash_file = settings.vault_path / "_agent" / "trash" / "Kunden" / "TestKunde" / "Angebot.pdf"
    assert trash_file.exists()
    assert trash_file.read_text() == "Inhalt"
    assert result["trash_path"] == "_agent/trash/Kunden/TestKunde/Angebot.pdf"


def test_vault_delete_moves_folder_recursively(tmp_path, monkeypatch):
    settings = _fake(tmp_path, monkeypatch)
    ordner = tmp_path / "Marketing" / "Alt"
    ordner.mkdir(parents=True)
    (ordner / "notiz.md").write_text("x")

    result = svc.vault_delete("Marketing/Alt")

    assert result["ok"] is True
    assert not ordner.exists()
    assert (settings.vault_path / "_agent" / "trash" / "Marketing" / "Alt" / "notiz.md").exists()


def test_vault_delete_avoids_collision_in_trash(tmp_path, monkeypatch):
    settings = _fake(tmp_path, monkeypatch)
    d = tmp_path / "Memos"
    d.mkdir()
    (d / "a.md").write_text("erste Version")

    r1 = svc.vault_delete("Memos/a.md")
    assert r1["ok"] is True

    (d / "a.md").write_text("zweite Version")
    r2 = svc.vault_delete("Memos/a.md")
    assert r2["ok"] is True
    assert r1["trash_path"] != r2["trash_path"]
    # Beide Versionen bleiben erhalten, keine wurde stillschweigend überschrieben.
    assert (settings.vault_path / r1["trash_path"]).read_text() == "erste Version"
    assert (settings.vault_path / r2["trash_path"]).read_text() == "zweite Version"


def test_vault_delete_rejects_path_outside_vault(tmp_path, monkeypatch):
    _fake(tmp_path, monkeypatch)
    result = svc.vault_delete("../../etc/passwd")
    assert result["ok"] is False


def test_vault_delete_reports_missing_file(tmp_path, monkeypatch):
    _fake(tmp_path, monkeypatch)
    result = svc.vault_delete("Kunden/Nichtvorhanden.pdf")
    assert result["ok"] is False
    assert "Nicht gefunden" in result["error"]


def test_vault_delete_never_calls_rmtree_or_unlink(tmp_path, monkeypatch):
    """Regressionsschutz: stellt sicher, dass niemand versehentlich wieder
    echtes Loeschen einbaut, ohne dass ein Test es bemerkt."""
    calls = []
    monkeypatch.setattr(svc.shutil, "rmtree", lambda *a, **kw: calls.append("rmtree"))
    settings = _fake(tmp_path, monkeypatch)
    d = tmp_path / "Sales" / "Alt"
    d.mkdir(parents=True)
    (d / "f.txt").write_text("x")

    svc.vault_delete("Sales/Alt")

    assert calls == []
    assert (settings.vault_path / "_agent" / "trash" / "Sales" / "Alt" / "f.txt").exists()
