"""Application configuration via environment variables."""
from __future__ import annotations

import os
import warnings
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Core
    app_name: str = "CodeForge AI"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/app"

    # Security
    secret_key: str = "dev-secret-key"
    session_secret: str = "dev-session-secret"
    session_max_age: int = 60 * 60 * 24 * 7  # 7 days
    session_cookie_name: str = "forge_session"
    csrf_enabled: bool = True

    # UI defaults
    default_language: Literal["en", "ar"] = "en"
    default_theme: Literal["dark", "light"] = "dark"

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    # AI
    ai_provider: str = ""
    ai_api_key: str = ""
    ai_model: str = ""
    ai_base_url: str = ""

    # RAG
    rag_enabled: bool = True
    rag_top_k: int = 5

    # Docker
    docker_enabled: bool = True

    # Workspace
    workspace_root: str = "/workspaces"

    # CORS
    cors_origins: str = ""

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60

    @property
    def cors_origin_list(self) -> list[str]:
        if not self.cors_origins:
            return []
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def google_configured(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def ai_configured(self) -> bool:
        return bool(self.ai_provider and self.ai_api_key)

    @property
    def is_production(self) -> bool:
        return not self.debug

    def warn_insecure_defaults(self) -> list[str]:
        issues: list[str] = []
        if self.is_production:
            if self.secret_key == "dev-secret-key":
                issues.append("SECRET_KEY is still the dev default — set a strong value.")
            if self.session_secret == "dev-session-secret":
                issues.append("SESSION_SECRET is still the dev default — set a strong value.")
            if self.debug:
                issues.append("DEBUG is true in production — set DEBUG=false.")
        return issues


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
