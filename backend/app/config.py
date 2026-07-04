"""Zentrale Konfiguration. Alle Pfade/Secrets kommen aus ENV statt hartcodiert,
damit Backend sowohl lokal als auch im Docker-Container auf jedem Host läuft."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    vault_path: Path = Path.home() / "Documents" / "Prozessia-Brain"
    anthropic_api_key: str = ""
    session_secret: str = "change-me"  # signiert Session-Cookies, MUSS in Prod überschrieben werden
    cors_origin: str = "http://localhost:5173"
    # Datei statt ENV-Variable: bcrypt-Hashes enthalten "$"-Zeichen, die docker-compose
    # in env_file-Werten als Variablen-Interpolation missversteht und stillschweigend
    # kaputt schreibt ($2b$12$... würde zu Teilen verschwinden). Siehe .env.example.
    users_file: Path = Path("users.json")

    # ── LinkedIn / Buffer ─────────────────────────────────────────────────────
    buffer_api_token: str = ""
    # IDs der Buffer-Kanäle (Sebastian + Prozessia Page)
    buffer_channel_sebastian: str = "6a25d2578f1d11f9b260c5ee"
    buffer_channel_prozessia: str = "6a25d2578f1d11f9b260c5ef"

    # ── Git-Sync ──────────────────────────────────────────────────────────────
    # Personal Access Token für git pull/push aus dem Docker-Container heraus.
    # Format: ghp_xxxx  → wird als HTTPS-Credential in die Remote-URL eingebettet.
    git_pat: str = ""

    # ── Onboarding-Automatisierung ────────────────────────────────────────────
    google_service_account_json: str = ""
    drive_kunden_folder_id: str = ""
    github_token: str = ""
    github_org: str = "Prozessia"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    notification_email: str = ""

    @property
    def avv_template_path(self) -> Path:
        return Path(__file__).resolve().parent.parent / "templates" / "AVV_Prozessia_TEMPLATE.docx"

    @property
    def agent_dir(self) -> Path:
        return self.vault_path / "_agent"

    @property
    def rag_index_path(self) -> Path:
        return self.agent_dir / "vault.index"

    @property
    def rag_meta_path(self) -> Path:
        return self.agent_dir / "vault_metadata.json"

    @property
    def memory_path(self) -> Path:
        return self.agent_dir / "memory.md"

    @property
    def context_path(self) -> Path:
        return self.agent_dir / "context.md"

    @property
    def prozessia_path(self) -> Path:
        return self.agent_dir / "prozessia.md"

    @property
    def conversations_dir(self) -> Path:
        return self.agent_dir / "conversations"

    @property
    def email_cache_dir(self) -> Path:
        return self.agent_dir / "email_cache"

    @property
    def inbox_dir(self) -> Path:
        return self.vault_path / "_inbox"

    @property
    def autoposter_dir(self) -> Path:
        return self.inbox_dir / "Branding" / "claude-linkedin-auto-poster"


@lru_cache
def get_settings() -> Settings:
    return Settings()
