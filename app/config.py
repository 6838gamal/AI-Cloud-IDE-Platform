"""Application configuration via environment variables."""
from __future__ import annotations

import os
import warnings
from functools import lru_cache
from typing import Literal, Optional

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
    version: str = "1.0.0"  # أضفت هذا المتغير

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
        """التحقق من تهيئة Google OAuth."""
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def google_configured_value(self) -> bool:
        """نفس google_configured ولكن مع اسم مختلف لتجنب الالتباس."""
        return self.google_configured

    @property
    def ai_configured(self) -> bool:
        return bool(self.ai_provider and self.ai_api_key)

    @property
    def is_production(self) -> bool:
        return not self.debug

    def get_template_vars(self) -> dict:
        """إرجاع المتغيرات التي يمكن استخدامها في القوالب."""
        return {
            "app_name": self.app_name,
            "app_version": self.version,
            "default_language": self.default_language,
            "default_theme": self.default_theme,
            "google_configured": self.google_configured,
            "debug": self.debug,
        }

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

# ===== تحقق من الإعدادات عند التحميل =====
def validate_settings():
    """التحقق من صحة الإعدادات وطباعة تحذيرات."""
    print("=" * 50)
    print("🔧 Application Settings")
    print("=" * 50)
    print(f"App Name: {settings.app_name}")
    print(f"Debug Mode: {settings.debug}")
    print(f"Database: {settings.database_url.split('@')[0] if '@' in settings.database_url else settings.database_url}...")
    print(f"Google OAuth: {'✅ Configured' if settings.google_configured else '❌ Not Configured'}")
    print(f"AI Provider: {settings.ai_provider if settings.ai_configured else '❌ Not Configured'}")
    print(f"Default Theme: {settings.default_theme}")
    print(f"Default Language: {settings.default_language}")
    print("=" * 50)
    
    # التحذيرات
    warnings = settings.warn_insecure_defaults()
    if warnings:
        print("⚠️ Warnings:")
        for warning in warnings:
            print(f"   - {warning}")
        print("=" * 50)

# تنفيذ التحقق عند التحميل (يمكنك تعليق هذا السطر إذا كان يسبب مشاكل)
try:
    validate_settings()
except Exception as e:
    print(f"⚠️ Settings validation error: {e}")

# ===== دالة مساعدة للحصول على إعدادات القالب بأمان =====
def get_template_settings() -> dict:
    """إرجاع إعدادات آمنة للاستخدام في القوالب."""
    return {
        "app_name": settings.app_name,
        "app_version": getattr(settings, "version", "1.0.0"),
        "default_language": settings.default_language,
        "default_theme": settings.default_theme,
        "google_configured": bool(settings.google_configured),
        "debug": settings.debug,
    }
