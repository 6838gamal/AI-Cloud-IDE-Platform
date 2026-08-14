"""User Pydantic schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    name: str = ""
    profile_picture: str | None = None
    language: str = "en"
    theme: str = "dark"


class UserCreate(UserBase):
    google_id: str | None = None


class UserUpdate(BaseModel):
    name: str | None = None
    profile_picture: str | None = None
    language: str | None = Field(None, pattern="^(en|ar)$")
    theme: str | None = Field(None, pattern="^(dark|light)$")


class UserOut(UserBase):
    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
