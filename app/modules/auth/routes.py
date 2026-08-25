"""Auth routes: Google OAuth login/callback, logout."""
from __future__ import annotations

from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.security import create_signed_payload, verify_signed_payload
from app.config import settings, get_template_settings
from app.database import get_db
from app.dependencies import CurrentUser, DbSession
from app.modules.auth.services import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

# ===== تحديد مسار القوالب بشكل صحيح =====
from pathlib import Path

# تحديد المسار الصحيح للمجلد templates
BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"

# التحقق من وجود المجلد
if not TEMPLATES_DIR.exists():
    # محاولة مسار بديل
    TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
    
    if not TEMPLATES_DIR.exists():
        # محاولة مسار آخر
        TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

print(f"📁 Templates directory: {TEMPLATES_DIR}")
print(f"✅ templates/auth/login.html exists: {(TEMPLATES_DIR / 'auth' / 'login.html').exists()}")
print(f"✅ templates/base.html exists: {(TEMPLATES_DIR / 'base.html').exists()}")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# ===== دالة مساعدة لإنشاء سياق القالب =====
def get_template_context(request: Request, extra: dict = None) -> dict:
    """
    إنشاء سياق القالب الأساسي مع المتغيرات العامة.
    
    Args:
        request: كائن الطلب من FastAPI
        extra: قاموس إضافي للدمج مع السياق الأساسي
        
    Returns:
        قاموس السياق الكامل للقالب
    """
    # استخدام الدالة المساعدة من ملف الإعدادات
    template_settings = get_template_settings()
    
    # السياق الأساسي
    context = {
        "request": request,
        **template_settings,  # دمج جميع إعدادات القالب
    }
    
    # دمج المتغيرات الإضافية
    if extra:
        context.update(extra)
    
    return context


# ===== وظيفة مساعدة لإنشاء رابط Google OAuth =====
def get_google_auth_url(request: Request) -> tuple[str, bool]:
    """
    إنشاء رابط Google OAuth والتحقق من التهيئة.
    
    Returns:
        tuple: (google_auth_url, google_configured)
    """
    google_auth_url = ""
    google_configured = settings.google_configured
    
    if google_configured:
        try:
            state = create_signed_payload({"nonce": "google_login"})
            request.session["oauth_state"] = state
            google_auth_url = AuthService.get_google_auth_url(state)
            print(f"✅ Google OAuth URL generated successfully")
        except Exception as e:
            print(f"⚠️ خطأ في إنشاء رابط Google: {e}")
            google_configured = False
            # محاولة الحصول على الرابط بدون session
            try:
                google_auth_url = AuthService.get_google_auth_url("")
            except:
                pass
    
    return google_auth_url, google_configured


@router.get("/login")
async def login_page(request: Request, user: CurrentUser = None):
    """
    عرض صفحة تسجيل الدخول.
    
    Args:
        request: كائن الطلب
        user: المستخدم الحالي (إذا كان مسجلاً)
        
    Returns:
        TemplateResponse أو RedirectResponse
    """
    # إذا كان المستخدم مسجلاً بالفعل، إعادة توجيه إلى لوحة التحكم
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    # تجهيز بيانات Google
    google_auth_url, google_configured = get_google_auth_url(request)
    
    # بناء سياق القالب
    context = get_template_context(request, {
        "google_auth_url": google_auth_url,
        "google_configured": google_configured,
        "page_title": "تسجيل الدخول",
    })
    
    # عرض صفحة تسجيل الدخول مع معالجة الأخطاء
    try:
        return templates.TemplateResponse("auth/login.html", context)
    except TypeError as e:
        print(f"❌ خطأ في TemplateResponse (TypeError): {e}")
        # محاولة بديلة بدون المتغيرات العامة المعقدة
        try:
            return templates.TemplateResponse(
                "auth/login.html", 
                {
                    "request": request,
                    "google_auth_url": google_auth_url,
                    "google_configured": False,
                    "app_name": settings.app_name,
                    "app_version": getattr(settings, "version", "1.0.0"),
                    "default_language": settings.default_language,
                    "default_theme": settings.default_theme,
                    "page_title": "تسجيل الدخول",
                }
            )
        except Exception as e2:
            print(f"❌ خطأ في المحاولة الثانية: {e2}")
            # محاولة ثالثة بسيطة جداً
            return templates.TemplateResponse(
                "auth/login.html", 
                {
                    "request": request,
                    "google_auth_url": "",
                    "google_configured": False,
                    "app_name": "AI Builder",
                }
            )
    except Exception as e:
        print(f"❌ خطأ غير متوقع في TemplateResponse: {e}")
        # عرض صفحة خطأ بسيطة
        try:
            return templates.TemplateResponse(
                "auth/login.html", 
                {
                    "request": request,
                    "google_auth_url": "",
                    "google_configured": False,
                    "app_name": "AI Builder",
                }
            )
        except:
            # في حالة فشل كل شيء، إعادة توجيه بسيطة
            return RedirectResponse(url="/", status_code=302)


@router.get("/google/callback")
async def google_callback(
    request: Request, 
    code: str = "", 
    state: str = "", 
    error: str = "",
    db: AsyncSession = Depends(get_db)
):
    """
    معالج رد Google OAuth.
    
    Args:
        request: كائن الطلب
        code: رمز التفويض من Google
        state: حالة الأمان من Google
        error: رسالة الخطأ (إن وجدت)
        db: جلسة قاعدة البيانات
        
    Returns:
        RedirectResponse
    """
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
        print(f"⚠️ OAuth state mismatch: stored={stored_state[:20] if stored_state else 'None'}, received={state[:20]}")
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
        print(f"✅ Cookie set successfully: {settings.session_cookie_name}")
    except Exception as e:
        print(f"⚠️ Cookie setting error: {e}")
    
    return response


@router.post("/logout")
async def logout(
    request: Request, 
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db)
):
    """
    تسجيل الخروج.
    
    Args:
        request: كائن الطلب
        user: المستخدم الحالي
        db: جلسة قاعدة البيانات
        
    Returns:
        RedirectResponse
    """
    token = request.cookies.get(settings.session_cookie_name)
    
    if token:
        try:
            auth_service = AuthService(db)
            success = await auth_service.delete_session(token)
            if success:
                print("✅ Session deleted successfully")
            else:
                print("⚠️ Session deletion failed or session not found")
        except Exception as e:
            print(f"⚠️ Session deletion error: {e}")
    
    # إنشاء استجابة تسجيل الخروج
    response = RedirectResponse(url="/auth/login", status_code=302)
    
    try:
        response.delete_cookie(settings.session_cookie_name, path="/")
        print("✅ Cookie deleted successfully")
    except Exception as e:
        print(f"⚠️ Cookie deletion error: {e}")
    
    return response


# ===== راوت إضافي للتحقق من صحة القوالب =====
@router.get("/debug/templates")
async def debug_templates(request: Request):
    """
    راوت للتحقق من القوالب (للتطوير فقط).
    
    Returns:
        JSON مع معلومات التصحيح
    """
    try:
        # محاولة تحميل القالب
        template = templates.get_template("auth/login.html")
        
        # الحصول على إعدادات القالب
        template_settings = get_template_settings()
        
        return {
            "status": "success",
            "template": "auth/login.html",
            "template_exists": True,
            "templates_dir": str(TEMPLATES_DIR),
            "settings": template_settings,
            "google_configured": bool(settings.google_configured),
            "app_name": settings.app_name,
            "session_cookie_name": settings.session_cookie_name,
            "debug": settings.debug,
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


# ===== راوت للتحقق من صحة الإعدادات =====
@router.get("/debug/settings")
async def debug_settings():
    """
    راوت لعرض الإعدادات (للتطوير فقط).
    
    Returns:
        JSON مع معلومات الإعدادات (مع إخفاء المعلومات الحساسة)
    """
    return {
        "app_name": settings.app_name,
        "debug": settings.debug,
        "google_configured": settings.google_configured,
        "default_language": settings.default_language,
        "default_theme": settings.default_theme,
        "database_url": settings.database_url.split("@")[0] + "@..." if "@" in settings.database_url else "configured",
        "has_google_client_id": bool(settings.google_client_id),
        "has_google_client_secret": bool(settings.google_client_secret),
        "session_cookie_name": settings.session_cookie_name,
        "cors_origins": settings.cors_origin_list,
        "rate_limit_enabled": settings.rate_limit_enabled,
        "ai_configured": settings.ai_configured,
        "rag_enabled": settings.rag_enabled,
        "docker_enabled": settings.docker_enabled,
    }
