"""Auth schemas."""
from __future__ import annotations

from pydantic import BaseModel


class GoogleUserInfo(BaseModel):
    sub: str
    email: str
    name: str = ""
    picture: str | None = None


class SessionInfo(BaseModel):
    token: str
    user_id: str
