"""Auth routes: Google OAuth login/callback, logout."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.common.security import create_signed_payload, verify_signed_payload
from app.config import settings
from app.dependencies import CurrentUser, DbSession
from app.modules.auth.services import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="templates")


@router.get("/login")
async def login_page(request: Request, user: CurrentUser):
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    google_auth_url = ""
    if settings.google_configured:
        state = create_signed_payload({"nonce": "google_login"})
        request.session["oauth_state"] = state
        google_auth_url = AuthService.get_google_auth_url(state)
    return templates.TemplateResponse("auth/login.html", {
        "request": request,
        "google_auth_url": google_auth_url,
        "google_configured": settings.google_configured,
    })


@router.get("/google/callback")
async def google_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error:
        return RedirectResponse(url="/auth/login?error=google_denied", status_code=302)
    if not code or not state:
        return RedirectResponse(url="/auth/login?error=missing_params", status_code=302)

    stored_state = request.session.get("oauth_state")
    if not stored_state or stored_state != state:
        return RedirectResponse(url="/auth/login?error=state_mismatch", status_code=302)
    verified = verify_signed_payload(state, max_age=600)
    if not verified:
        return RedirectResponse(url="/auth/login?error=invalid_state", status_code=302)

    request.session.pop("oauth_state", None)
    db = request.state.db
    auth_service = AuthService(db)
    user_id = await auth_service.login_with_google(code)
    if not user_id:
        return RedirectResponse(url="/auth/login?error=login_failed", status_code=302)

    token = await auth_service.create_session(
        user_id=user_id,
        ip=request.client.host if request.client else None,
        ua=request.headers.get("user-agent"),
    )
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
async def logout(request: Request, user: CurrentUser):
    db = request.state.db
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        auth_service = AuthService(db)
        await auth_service.delete_session(token)
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie(settings.session_cookie_name)
    return response
