"""Configurações do aplicativo usando Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações centralizadas do Smart Invest."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Permitir variáveis extras no .env
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

    # Segurança
    secret_key: str = "change-me-in-production-minimum-32-chars-long"

    # Configurações
    cache_ttl_hours: int = 1
    request_timeout_seconds: int = 30
    max_retries: int = 3

    @property
    def is_development(self) -> bool:
        """Retorna True se ambiente é desenvolvimento."""
        return self.environment.lower() in ("development", "dev", "local")

    @property
    def is_production(self) -> bool:
        """Retorna True se ambiente é produção."""
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
        """Retorna True se token brapi está configurado."""
        return self.brapi_token is not None and len(self.brapi_token) > 0


@lru_cache()
def get_settings() -> Settings:
    """
    Retorna instância singleton de Settings.
    
    Usa LRU cache para evitar recriação múltipla.
    """
    return Settings()
