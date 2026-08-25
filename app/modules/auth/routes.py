"""Auth routes: Google OAuth login/callback, logout."""
from __future__ import annotations

from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.security import create_signed_payload, verify_signed_payload
from app.config import settings
from app.database import get_db
from app.dependencies import CurrentUser, DbSession
from app.modules.auth.services import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

# ===== تحديد مسار القوالب بشكل صحيح =====
from pathlib import Path
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ===== إضافة متغيرات عامة للقوالب =====
templates.env.globals.update({
    "app_name": getattr(settings, "app_name", "AI Builder"),
    "app_version": getattr(settings, "version", "1.0.0"),
    "default_language": getattr(settings, "default_language", "ar"),
    "default_theme": getattr(settings, "default_theme", "dark"),
})


@router.get("/login")
async def login_page(request: Request, user: CurrentUser = None):
    """عرض صفحة تسجيل الدخول."""
    # إذا كان المستخدم مسجلاً بالفعل، إعادة توجيه إلى لوحة التحكم
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    # إنشاء رابط Google OAuth
    google_auth_url = ""
    if settings.google_configured:
        try:
            state = create_signed_payload({"nonce": "google_login"})
            request.session["oauth_state"] = state
            google_auth_url = AuthService.get_google_auth_url(state)
        except Exception as e:
            print(f"⚠️ خطأ في إنشاء رابط Google: {e}")
    
    # عرض صفحة تسجيل الدخول
    return templates.TemplateResponse("auth/login.html", {
        "request": request,
        "google_auth_url": google_auth_url,
        "google_configured": settings.google_configured,
    })


@router.get("/google/callback")
async def google_callback(
    request: Request, 
    code: str = "", 
    state: str = "", 
    error: str = "",
    db: AsyncSession = Depends(get_db)
):
    """معالج رد Google OAuth."""
    # التحقق من وجود أخطاء
    if error:
        return RedirectResponse(url="/auth/login?error=google_denied", status_code=302)
    if not code or not state:
        return RedirectResponse(url="/auth/login?error=missing_params", status_code=302)

    # التحقق من حالة OAuth
    stored_state = request.session.get("oauth_state")
    if not stored_state or stored_state != state:
        return RedirectResponse(url="/auth/login?error=state_mismatch", status_code=302)
    
    # التحقق من صحة التوقيع
    verified = verify_signed_payload(state, max_age=600)
    if not verified:
        return RedirectResponse(url="/auth/login?error=invalid_state", status_code=302)

    # حذف حالة OAuth من الجلسة
    request.session.pop("oauth_state", None)
    
    # تسجيل الدخول باستخدام Google
    auth_service = AuthService(db)
    user_id = await auth_service.login_with_google(code)
    if not user_id:
        return RedirectResponse(url="/auth/login?error=login_failed", status_code=302)

    # إنشاء جلسة جديدة
    token = await auth_service.create_session(
        user_id=user_id,
        ip=request.client.host if request.client else None,
        ua=request.headers.get("user-agent"),
    )
    
    # إنشاء استجابة مع كوكي الجلسة
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        secure=not settings.debug,
        max_age=settings.session_max_age,
    )
    return response


@router.post("/logout")
async def logout(
    request: Request, 
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db)
):
    """تسجيل الخروج."""
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        auth_service = AuthService(db)
        await auth_service.delete_session(token)
    
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie(settings.session_cookie_name)
    return response
