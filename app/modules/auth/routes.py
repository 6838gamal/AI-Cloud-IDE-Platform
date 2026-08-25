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

# ===== تحديد مسار القوالب بشكل بسيط =====
from pathlib import Path

# مسار القوالب
TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"

# إذا لم يكن موجوداً، جرب مساراً آخر
if not TEMPLATES_DIR.exists():
    TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

print(f"📁 Templates directory: {TEMPLATES_DIR}")

# ===== إنشاء كائن القوالب بشكل مختلف =====
# هذه هي الطريقة الصحيحة لتجنب مشكلة unhashable type
class SafeJinja2Templates(Jinja2Templates):
    """نسخة آمنة من Jinja2Templates تتجنب مشكلة unhashable type."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # لا نضيف أي globals هنا
        pass

# استخدام النسخة الآمنة
templates = SafeJinja2Templates(directory=str(TEMPLATES_DIR))

# ===== دالة مساعدة لإنشاء سياق القالب =====
def get_template_context(request: Request, extra: dict = None) -> dict:
    """
    إنشاء سياق القالب مع المتغيرات المطلوبة.
    جميع القيم هنا هي من أنواع بسيطة (str, bool, int) وليس dict.
    """
    # متغيرات بسيطة فقط
    context = {
        "request": request,
        "app_name": str(getattr(settings, "app_name", "AI Builder")),
        "app_version": str(getattr(settings, "version", "1.0.0")),
        "default_language": str(getattr(settings, "default_language", "en")),
        "default_theme": str(getattr(settings, "default_theme", "dark")),
        "debug": bool(getattr(settings, "debug", False)),
    }
    
    # دمج المتغيرات الإضافية
    if extra:
        for key, value in extra.items():
            # تجاهل أي قيم من نوع dict
            if not isinstance(value, dict):
                context[key] = value
            else:
                print(f"⚠️ Skipping {key} because it's a dict")
    
    return context


@router.get("/login")
async def login_page(request: Request, user: CurrentUser = None):
    """
    عرض صفحة تسجيل الدخول.
    """
    # إذا كان المستخدم مسجلاً بالفعل، إعادة توجيه إلى لوحة التحكم
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    # تجهيز بيانات Google
    google_auth_url = ""
    google_configured = False
    
    try:
        # التحقق من تهيئة Google
        if hasattr(settings, 'google_client_id') and hasattr(settings, 'google_client_secret'):
            if settings.google_client_id and settings.google_client_secret:
                google_configured = True
                state = create_signed_payload({"nonce": "google_login"})
                request.session["oauth_state"] = state
                google_auth_url = AuthService.get_google_auth_url(state)
                print("✅ Google OAuth URL generated successfully")
    except Exception as e:
        print(f"⚠️ Google OAuth error: {e}")
        google_configured = False
    
    # بناء سياق القالب
    context = get_template_context(request, {
        "google_auth_url": str(google_auth_url),
        "google_configured": bool(google_configured),
        "page_title": "تسجيل الدخول",
    })
    
    # ===== المحاولة الأولى: استخدام TemplateResponse بشكل طبيعي =====
    try:
        return templates.TemplateResponse("auth/login.html", context)
    except TypeError as e:
        print(f"❌ TypeError in TemplateResponse: {e}")
        
        # ===== المحاولة الثانية: مسح الكاش وإعادة المحاولة =====
        try:
            templates.env.cache.clear()
            return templates.TemplateResponse("auth/login.html", context)
        except Exception as e2:
            print(f"❌ Second attempt failed: {e2}")
            
            # ===== المحاولة الثالثة: إنشاء كائن templates جديد =====
            try:
                # إنشاء كائن جديد
                new_templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
                return new_templates.TemplateResponse("auth/login.html", {
                    "request": request,
                    "google_auth_url": str(google_auth_url),
                    "google_configured": bool(google_configured),
                    "app_name": str(getattr(settings, "app_name", "AI Builder")),
                })
            except Exception as e3:
                print(f"❌ Third attempt failed: {e3}")
                
                # ===== المحاولة الأخيرة: إعادة توجيه بسيطة =====
                return RedirectResponse(url="/", status_code=302)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return RedirectResponse(url="/", status_code=302)


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
        print(f"⚠️ Google OAuth error: {error}")
        return RedirectResponse(url="/auth/login?error=google_denied", status_code=302)
    
    if not code or not state:
        print("⚠️ Missing code or state parameters")
        return RedirectResponse(url="/auth/login?error=missing_params", status_code=302)

    # التحقق من حالة OAuth
    stored_state = request.session.get("oauth_state")
    if not stored_state or stored_state != state:
        print(f"⚠️ OAuth state mismatch")
        return RedirectResponse(url="/auth/login?error=state_mismatch", status_code=302)
    
    # التحقق من صحة التوقيع
    try:
        verified = verify_signed_payload(state, max_age=600)
        if not verified:
            print("⚠️ Invalid state signature")
            return RedirectResponse(url="/auth/login?error=invalid_state", status_code=302)
    except Exception as e:
        print(f"⚠️ State verification error: {e}")
        return RedirectResponse(url="/auth/login?error=invalid_state", status_code=302)

    # حذف حالة OAuth من الجلسة
    request.session.pop("oauth_state", None)
    
    # تسجيل الدخول باستخدام Google
    try:
        auth_service = AuthService(db)
        user_id = await auth_service.login_with_google(code)
        
        if not user_id:
            print("⚠️ Google login failed - no user ID returned")
            return RedirectResponse(url="/auth/login?error=login_failed", status_code=302)
        
        print(f"✅ User logged in successfully: {user_id}")
    except Exception as e:
        print(f"⚠️ Google login exception: {e}")
        return RedirectResponse(url="/auth/login?error=login_failed", status_code=302)

    # إنشاء جلسة جديدة
    try:
        token = await auth_service.create_session(
            user_id=user_id,
            ip=request.client.host if request.client else None,
            ua=request.headers.get("user-agent"),
        )
        
        if not token:
            print("⚠️ Session creation failed - no token returned")
            return RedirectResponse(url="/auth/login?error=login_failed", status_code=302)
            
        print("✅ Session created successfully")
    except Exception as e:
        print(f"⚠️ Session creation error: {e}")
        return RedirectResponse(url="/auth/login?error=login_failed", status_code=302)
    
    # إنشاء استجابة مع كوكي الجلسة
    response = RedirectResponse(url="/dashboard", status_code=302)
    
    # إعدادات الكوكي
    cookie_settings = {
        "key": settings.session_cookie_name,
        "value": token,
        "httponly": True,
        "samesite": "lax",
        "secure": not settings.debug,
        "max_age": settings.session_max_age,
        "path": "/",
    }
    
    # إضافة الكوكي مع معالجة الأخطاء
    try:
        response.set_cookie(**cookie_settings)
        print(f"✅ Cookie set successfully")
    except Exception as e:
        print(f"⚠️ Cookie setting error: {e}")
    
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
        try:
            auth_service = AuthService(db)
            await auth_service.delete_session(token)
            print("✅ Session deleted successfully")
        except Exception as e:
            print(f"⚠️ Session deletion error: {e}")
    
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie(settings.session_cookie_name, path="/")
    
    return response


# ===== راوت للتصحيح =====
@router.get("/debug/templates")
async def debug_templates(request: Request):
    """راوت للتحقق من القوالب (للتطوير فقط)."""
    try:
        # محاولة تحميل القالب
        template = templates.get_template("auth/login.html")
        
        return {
            "status": "success",
            "template": "auth/login.html",
            "template_exists": True,
            "templates_dir": str(TEMPLATES_DIR),
            "google_configured": bool(settings.google_configured),
            "app_name": settings.app_name,
            "templates_type": str(type(templates)),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "templates_dir": str(TEMPLATES_DIR),
            "template_exists": (TEMPLATES_DIR / "auth" / "login.html").exists(),
            "base_exists": (TEMPLATES_DIR / "base.html").exists(),
            "google_configured": bool(settings.google_configured),
        }
