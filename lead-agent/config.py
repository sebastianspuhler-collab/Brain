"""Zentrale Konfiguration des Lead-Agenten. Eigene, schmale Settings-Klasse
(nicht backend/app/config.py importiert) - dieser Container läuft isoliert
(eigenes Docker-Netzwerk lead-agent-bridge, siehe docker-compose.yml) und soll
nicht die restlichen Backend-Secrets (SMTP, Buffer, Google, ...) sehen, auch
wenn er sie netzwerkseitig ohnehin nicht erreichen könnte - gleiche Begründung
wie dev-agent/.env.example."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Vault-Mount (anders als dev-agent: der Lead-Agent muss Leads/*.md lesen
    # und schreiben können, siehe vault_leads.py - dev-agent arbeitet dagegen
    # ausschließlich in einem vault-fremden /workspace-Volume).
    vault_path: Path = Path("/vault")

    # ── Close CRM ────────────────────────────────────────────────────────────
    close_api_key: str = ""
    close_api_base: str = "https://api.close.com/api/v1"
    # Signing-Secret aus Close (Settings -> Webhooks -> gewählter Webhook ->
    # "Signing key") für die HMAC-Verifikation eingehender Events, siehe
    # webhooks.py. Ohne gesetztes Secret werden Webhooks abgelehnt (fail-closed
    # - ein öffentlich erreichbarer, unauthentifizierter Endpunkt wäre sonst
    # ein offenes Tor in den Vault).
    close_webhook_signing_key: str = ""
    # Custom-Field-ID (nicht der Anzeigename!) für das "Quelle"-Feld, das neue
    # Leads als "prozessia-lead-agent" markiert - Close erzeugt Custom Fields
    # nur über die UI/API vorab, die ID muss nach dem Anlegen hier eingetragen
    # werden (siehe README.md, Punkt "Close-Setup").
    close_source_field_id: str = ""
    close_source_value: str = "prozessia-lead-agent"

    @property
    def leads_dir(self) -> Path:
        return self.vault_path / "Leads"


@lru_cache
def get_settings() -> Settings:
    return Settings()
