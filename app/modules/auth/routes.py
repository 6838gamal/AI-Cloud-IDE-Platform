"""Auth routes: Google OAuth login/callback, logout."""
from __future__ import annotations

from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.common.security import create_signed_payload, verify_signed_payload
from app.config import settings
from app.database import get_db
from app.dependencies import CurrentUser, DbSession
from app.modules.auth.services import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

# ===== تحديد مسار القوالب =====
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"

if not TEMPLATES_DIR.exists():
    TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

print(f"📁 Templates directory: {TEMPLATES_DIR}")

# ===== إنشاء بيئة Jinja2 يدوياً =====
# هذه هي الطريقة الصحيحة لتجنب مشكلة unhashable type
env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(['html', 'xml']),
    enable_async=True,
    cache_size=0,  # تعطيل الكاش تماماً
)

# ===== إنشاء كائن Jinja2Templates باستخدام البيئة المخصصة =====
templates = Jinja2Templates(env=env)


# ===== دالة مساعدة لإنشاء سياق القالب =====
def get_template_context(request: Request, extra: dict = None) -> dict:
    """إنشاء سياق القالب مع المتغيرات المطلوبة."""
    context = {
        "request": request,
        "app_name": str(settings.app_name),
        "app_version": str(getattr(settings, "version", "1.0.0")),
        "default_language": str(settings.default_language),
        "default_theme": str(settings.default_theme),
        "debug": bool(settings.debug),
        "google_configured": False,
        "google_auth_url": "",
    }
    
    if extra:
        # إضافة المتغيرات الإضافية مع التأكد من أنها بسيطة
        for key, value in extra.items():
            if not isinstance(value, (dict, list, set)):
                context[key] = value
            else:
                print(f"⚠️ Skipping {key} because it's not hashable: {type(value)}")
    
    return context


@router.get("/login")
async def login_page(request: Request, user: CurrentUser = None):
    """عرض صفحة تسجيل الدخول."""
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    # تجهيز بيانات Google
    google_auth_url = ""
    google_configured = False
    
    try:
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
    
    # بناء السياق
    context = get_template_context(request, {
        "google_auth_url": str(google_auth_url),
        "google_configured": bool(google_configured),
        "page_title": "تسجيل الدخول",
    })
    
    # عرض القالب مع معالجة الأخطاء
    try:
        # استخدام TemplateResponse مع السياق
        return templates.TemplateResponse("auth/login.html", context)
    except Exception as e:
        print(f"❌ Error in TemplateResponse: {e}")
        
        # محاولة بديلة: استخدام HTMLResponse مباشرة
        try:
            template = env.get_template("auth/login.html")
            html_content = await template.render_async(**context)
            return HTMLResponse(content=html_content)
        except Exception as e2:
            print(f"❌ Second attempt failed: {e2}")
            
            # المحاولة الأخيرة: عرض صفحة بسيطة
            return HTMLResponse(content="""
            <!DOCTYPE html>
            <html>
            <head><title>Login</title></head>
            <body>
                <h1>Login Page</h1>
                <p>Google OAuth: Not Configured</p>
                <a href="/">Go Home</a>
            </body>
            </html>
            """)


@router.get("/google/callback")
async def google_callback(
    request: Request, 
    code: str = "", 
    state: str = "", 
    error: str = "",
    db: AsyncSession = Depends(get_db)
):
    """معالج رد Google OAuth."""
    if error:
        print(f"⚠️ Google OAuth error: {error}")
        return RedirectResponse(url="/auth/login?error=google_denied", status_code=302)
    
    if not code or not state:
        print("⚠️ Missing code or state parameters")
        return RedirectResponse(url="/auth/login?error=missing_params", status_code=302)

    stored_state = request.session.get("oauth_state")
    if not stored_state or stored_state != state:
        print(f"⚠️ OAuth state mismatch")
        return RedirectResponse(url="/auth/login?error=state_mismatch", status_code=302)
    
    try:
        verified = verify_signed_payload(state, max_age=600)
        if not verified:
            print("⚠️ Invalid state signature")
            return RedirectResponse(url="/auth/login?error=invalid_state", status_code=302)
    except Exception as e:
        print(f"⚠️ State verification error: {e}")
        return RedirectResponse(url="/auth/login?error=invalid_state", status_code=302)

    request.session.pop("oauth_state", None)
    
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
    
    response = RedirectResponse(url="/dashboard", status_code=302)
    
    cookie_settings = {
        "key": settings.session_cookie_name,
        "value": token,
        "httponly": True,
        "samesite": "lax",
        "secure": not settings.debug,
        "max_age": settings.session_max_age,
        "path": "/",
    }
    
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
    """راوت للتحقق من القوالب."""
    try:
        # محاولة تحميل القالب باستخدام البيئة المخصصة
        template = env.get_template("auth/login.html")
        
        return {
            "status": "success",
            "template": "auth/login.html",
            "template_exists": True,
            "templates_dir": str(TEMPLATES_DIR),
            "google_configured": bool(settings.google_configured),
            "app_name": settings.app_name,
            "env_type": str(type(env)),
            "cache_size": env.cache.size if hasattr(env.cache, 'size') else "unknown",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "templates_dir": str(TEMPLATES_DIR),
            "template_exists": (TEMPLATES_DIR / "auth" / "login.html").exists(),
            "base_exists": (TEMPLATES_DIR / "base.html").exists(),
        }
