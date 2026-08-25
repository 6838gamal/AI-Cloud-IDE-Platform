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
    version: str = "1.0.0"

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

    # ===== الخصائص المحسوبة =====
    
    @property
    def cors_origin_list(self) -> list[str]:
        """قائمة عناوين CORS المسموح بها."""
        if not self.cors_origins:
            return []
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def google_configured(self) -> bool:
        """التحقق من تهيئة Google OAuth."""
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def ai_configured(self) -> bool:
        """التحقق من تهيئة AI."""
        return bool(self.ai_provider and self.ai_api_key)

    @property
    def is_production(self) -> bool:
        """التحقق من وضع الإنتاج."""
        return not self.debug

    @property
    def template_vars(self) -> dict:
        """
        إرجاع متغيرات آمنة للاستخدام في القوالب.
        جميع القيم من أنواع بسيطة (str, bool) لتجنب مشاكل التجزئة (hashing).
        """
        return {
            "app_name": str(self.app_name),
            "app_version": str(self.version),
            "default_language": str(self.default_language),
            "default_theme": str(self.default_theme),
            "google_configured": bool(self.google_configured),
            "debug": bool(self.debug),
            "session_cookie_name": str(self.session_cookie_name),
        }

    def warn_insecure_defaults(self) -> list[str]:
        """التحقق من الإعدادات غير الآمنة في وضع الإنتاج."""
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
    """الحصول على كائن الإعدادات مع التخزين المؤقت."""
    return Settings()


# ===== إنشاء كائن الإعدادات العالمي =====
settings = get_settings()


# ===== دالة التحقق من الإعدادات =====
def validate_settings():
    """التحقق من صحة الإعدادات وطباعة معلومات التصحيح."""
    print("=" * 50)
    print("🔧 Application Settings")
    print("=" * 50)
    print(f"App Name: {settings.app_name}")
    print(f"Version: {settings.version}")
    print(f"Debug Mode: {settings.debug}")
    
    # إخفاء تفاصيل قاعدة البيانات
    db_url = settings.database_url
    if "@" in db_url:
        parts = db_url.split("@")
        db_url = f"{parts[0].split('://')[0]}://***@{parts[1]}"
    print(f"Database: {db_url}")
    
    print(f"Google OAuth: {'✅ Configured' if settings.google_configured else '❌ Not Configured'}")
    print(f"AI Provider: {'✅ Configured' if settings.ai_configured else '❌ Not Configured'}")
    print(f"Default Theme: {settings.default_theme}")
    print(f"Default Language: {settings.default_language}")
    print(f"Session Cookie: {settings.session_cookie_name}")
    print("=" * 50)
    
    # التحذيرات
    warnings = settings.warn_insecure_defaults()
    if warnings:
        print("⚠️ Warnings:")
        for warning in warnings:
            print(f"   - {warning}")
        print("=" * 50)


# ===== دالة مساعدة للحصول على إعدادات القالب =====
def get_template_settings() -> dict:
    """
    إرجاع إعدادات آمنة للاستخدام في القوالب.
    هذه الدالة مخصصة للاستخدام في routes.
    """
    return settings.template_vars


# ===== تنفيذ التحقق عند التحميل =====
try:
    validate_settings()
except Exception as e:
    print(f"⚠️ Settings validation error: {e}")
