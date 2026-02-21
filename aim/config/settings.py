from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuracoes centralizadas do Smart Invest."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Ambiente
    environment: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    # Database
    database_url: str = "sqlite:///data/smart_invest.db"

    # API Keys
    brapi_token: Optional[str] = None
    brapi_base_url: str = "https://brapi.dev/api"

    # LLM (futuro)
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    # Seguranca
    secret_key: str = "change-me-in-production-minimum-32-chars-long"
    cors_allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    cors_allow_origin_regex: Optional[str] = None
    auth_cookie_name: str = "smart_invest_token"
    auth_cookie_secure: bool = False
    auth_cookie_samesite: str = "lax"

    # Configuracoes
    cache_ttl_hours: int = 1
    request_timeout_seconds: int = 30
    max_retries: int = 3
    audit_retention_days: int = 180
    audit_purge_interval_minutes: int = 60

    # Atualizacao automatica
    auto_update_on_startup: bool = True
    auto_update_daily_schedule: bool = True
    auto_update_hour: int = 19
    auto_update_minute: int = 5
    auto_update_weekdays_only: bool = True

    @property
    def is_development(self) -> bool:
        """Retorna True se ambiente e desenvolvimento."""
        return self.environment.lower() in ("development", "dev", "local")

    @property
    def is_production(self) -> bool:
        """Retorna True se ambiente e producao."""
        return self.environment.lower() == "production"

    @property
    def db_path(self) -> Path:
        """Retorna caminho do banco SQLite."""
        if self.database_url.startswith("sqlite:///"):
            path_str = self.database_url.replace("sqlite:///", "")
            return Path(path_str)
        return Path("data/smart_invest.db")

    @property
    def has_brapi_token(self) -> bool:
        """Retorna True se token brapi esta configurado."""
        return self.brapi_token is not None and len(self.brapi_token) > 0

    @property
    def cors_origins(self) -> list[str]:
        """Retorna lista de origins permitidas para CORS."""
        return [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]


@lru_cache()
def get_settings() -> Settings:
    """Retorna instancia singleton de Settings."""
    return Settings()
