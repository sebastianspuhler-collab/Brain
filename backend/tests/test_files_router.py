from app.routers.files import _SKIP


def test_app_code_dirs_excluded_from_vault_browser():
    """Vault und App-Code leben im selben Repo - der Datei-Browser soll trotzdem
    nur Vault-Inhalt zeigen, nicht den eigenen Python/React-Quellcode."""
    assert "backend" in _SKIP
    assert "frontend" in _SKIP
    assert "docker-compose.yml" in _SKIP


def test_vault_content_dirs_not_accidentally_excluded():
    for name in ("Kunden", "Finanzen", "Leads", "Marketing", "Sales", "Vertraege"):
        assert name not in _SKIP
