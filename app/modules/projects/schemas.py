"""Project schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    project_type: str = Field(default="python", pattern="^(python|fastapi|flask|django|streamlit|flutter)$")


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None


class ProjectOut(BaseModel):
    id: str
    user_id: str
    name: str
    slug: str
    description: str | None
    project_type: str
    status: str
    workspace_path: str | None
    container_id: str | None
    preview_port: int | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
