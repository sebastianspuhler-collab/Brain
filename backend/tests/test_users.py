import json

from app.config import get_settings
from app.security import hash_password
from app.users import get_password_hash, get_user_hashes, user_exists


def _clear_caches():
    get_settings.cache_clear()
    get_user_hashes.cache_clear()


def test_user_hashes_loaded_from_file(tmp_path, monkeypatch):
    hashed = hash_password("hunter2")
    users_file = tmp_path / "users.json"
    users_file.write_text(json.dumps({"amin": hashed}), encoding="utf-8")
    monkeypatch.setenv("USERS_FILE", str(users_file))
    _clear_caches()

    assert user_exists("amin")
    assert not user_exists("unknown")
    assert get_password_hash("amin") == hashed
    _clear_caches()


def test_missing_file_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("USERS_FILE", str(tmp_path / "does-not-exist.json"))
    _clear_caches()

    assert get_user_hashes() == {}
    assert not user_exists("amin")
    _clear_caches()


def test_malformed_file_returns_empty(tmp_path, monkeypatch):
    users_file = tmp_path / "users.json"
    users_file.write_text("not-json", encoding="utf-8")
    monkeypatch.setenv("USERS_FILE", str(users_file))
    _clear_caches()

    assert get_user_hashes() == {}
    _clear_caches()


def test_directory_at_users_file_path_returns_empty_instead_of_crashing(tmp_path, monkeypatch):
    """Reproduziert den Docker-Bind-Mount-Fall: fehlt users.json auf dem Host beim
    ersten 'docker compose up', legt Docker dort automatisch ein leeres Verzeichnis
    an. Das darf den Login-Endpoint nicht mit 500 abschießen."""
    users_dir = tmp_path / "users.json"
    users_dir.mkdir()
    monkeypatch.setenv("USERS_FILE", str(users_dir))
    _clear_caches()

    assert get_user_hashes() == {}
    assert not user_exists("amin")
    _clear_caches()
