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

    # ── Google Workspace Integration ────────────────────────────────────────
    google_service_account_json: str = ""
    google_credentials_json: str = ""  # OAuth für Gmail, Drive, etc.
    drive_kunden_folder_id: str = ""
    
    # ── Microsoft 365 Integration ──────────────────────────────────────────
    ms_client_id: str = ""
    ms_tenant_id: str = ""
    ms_client_secret: str = ""

    # ── LinkedIn / Buffer ─────────────────────────────────────────────────────
    buffer_api_token: str = ""
    # IDs der Buffer-Kanäle (Sebastian + Prozessia Page)
    buffer_channel_sebastian: str = "6a25d2578f1d11f9b260c5ee"
    buffer_channel_prozessia: str = "6a25d2578f1d11f9b260c5ef"

    # ── LinkedIn Karussell (Content-Engine + Bildgenerierung + Hosting) ───────
    # Interne Docker-Netzwerk-URL des content-engine-Service (siehe
    # docker-compose.yml) - liefert die Slide-Texte via Claude.
    content_engine_url: str = "http://content-engine:3002"
    openai_api_key: str = ""
    # ── OCR-Vorstufe für PDFs (Umsetzungsplan-Memo 2026-07-16, Punkt C1) ──────
    # Optional: ohne Key läuft die PDF-Extraktion wie bisher über PyPDF2 weiter
    # (automatischer Fallback in classify.extract_text()), kein Verhalten
    # ändert sich ohne diesen Key.
    mistral_api_key: str = ""
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""

    # ── YouTube / Buffer ──────────────────────────────────────────────────────
    # Kanal-ID des mit Buffer verbundenen YouTube-Kanals (Buffer-Dashboard →
    # Kanal-Einstellungen, ID steht in der URL). Ohne diese ID läuft kein Push.
    buffer_channel_youtube: str = ""
    # Öffentliche Basis-URL, unter der dieses Backend erreichbar ist (z.B.
    # https://brain.prozessia.space) - Buffer lädt das Video selbst von dort
    # herunter, braucht also eine stabile, öffentlich erreichbare, nicht
    # ablaufende URL. Fällt auf cors_origin zurück, wenn nicht gesetzt.
    public_base_url: str = ""
    # YouTube-Standardkategorie: 28 = Wissenschaft & Technik (passt zu KI-Content)
    youtube_default_category_id: str = "28"

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
        # Git-getrackt (Marketing/LinkedIn/) statt _inbox/ (gitignored) - sonst
        # geht z.B. die gesetzte Richtung (brain-direction.md) bei jedem
        # frischen Deploy verloren, weil _inbox/ nie committed wird.
        return self.vault_path / "Marketing" / "LinkedIn"

    @property
    def youtube_media_dir(self) -> Path:
        # Bewusst NICHT git-getrackt (*.mp4 steht in .gitignore) - die Dateien
        # müssen nur so lange auf dem VPS liegen, bis Buffer sie abgeholt hat,
        # und sind fürs Second-Brain-Gedächtnis irrelevant.
        return self.vault_path / "_agent" / "youtube_media"

    @property
    def public_media_base_url(self) -> str:
        return (self.public_base_url or self.cors_origin).rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()
