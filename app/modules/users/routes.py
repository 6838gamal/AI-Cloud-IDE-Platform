"""User routes."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.dependencies import RequiredUser
from app.modules.users.schemas import UserUpdate
from app.modules.users.services import UserService

router = APIRouter(prefix="/api/users", tags=["users"])
templates = Jinja2Templates(directory="templates")


@router.get("/me")
async def get_me(request: Request, user: RequiredUser):
    from app.dependencies import DbSession
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "profile_picture": user.profile_picture,
        "language": user.language,
        "theme": user.theme,
    }


@router.patch("/me")
async def update_me(request: Request, user: RequiredUser, data: UserUpdate):
    db = request.state.db
    service = UserService(db)
    updated = await service.update(user.id, data)
    return {
        "id": updated.id,
        "email": updated.email,
        "name": updated.name,
        "profile_picture": updated.profile_picture,
        "language": updated.language,
        "theme": updated.theme,
    }


@router.post("/me/language/{lang}")
async def set_language(request: Request, user: RequiredUser, lang: str):
    if lang not in ("en", "ar"):
        from app.common.exceptions import ValidationError
        raise ValidationError("Invalid language")
    db = request.state.db
    service = UserService(db)
    await service.update(user.id, UserUpdate(language=lang))
    referer = request.headers.get("referer", "/")
    return RedirectResponse(url=referer, status_code=303)


@router.post("/me/theme/{theme}")
async def set_theme(request: Request, user: RequiredUser, theme: str):
    if theme not in ("dark", "light"):
        from app.common.exceptions import ValidationError
        raise ValidationError("Invalid theme")
    db = request.state.db
    service = UserService(db)
    await service.update(user.id, UserUpdate(theme=theme))
    referer = request.headers.get("referer", "/")
    return RedirectResponse(url=referer, status_code=303)
