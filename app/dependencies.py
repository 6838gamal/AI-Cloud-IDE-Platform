"""Shared dependencies for routes."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.users.models import User

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(request: Request) -> User | None:
    user = getattr(request.state, "user", None)
    if user is None:
        return None
    return user


CurrentUser = Annotated[User | None, Depends(get_current_user)]


async def require_user(request: Request) -> User:
    user = getattr(request.state, "user", None)
    if user is None:
        from app.common.exceptions import AuthenticationRequiredError
        raise AuthenticationRequiredError()
    return user


RequiredUser = Annotated[User, Depends(require_user)]
