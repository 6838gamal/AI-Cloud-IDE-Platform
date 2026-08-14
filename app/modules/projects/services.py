"""Project service layer."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.utils import safe_join, slugify
from app.config import settings
from app.modules.projects.models import Project
from app.modules.projects.schemas import ProjectCreate, ProjectUpdate


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, project_id: str) -> Project | None:
        return await self.db.get(Project, project_id)

    async def get_for_user(self, project_id: str, user_id: str) -> Project | None:
        project = await self.get_by_id(project_id)
        if not project or project.user_id != user_id:
            return None
        return project

    async def list_for_user(self, user_id: str) -> list[Project]:
        result = await self.db.execute(
            select(Project).where(Project.user_id == user_id).order_by(Project.updated_at.desc())
        )
        return list(result.scalars().all())

    async def create(self, user_id: str, data: ProjectCreate) -> Project:
        slug = slugify(data.name)
        workspace_path = safe_join(settings.workspace_root, user_id, slug)
        Path(workspace_path).mkdir(parents=True, exist_ok=True)
        project = Project(
            user_id=user_id,
            name=data.name,
            slug=slug,
            description=data.description,
            project_type=data.project_type,
            workspace_path=workspace_path,
            status="stopped",
        )
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def update(self, project_id: str, user_id: str, data: ProjectUpdate) -> Project | None:
        project = await self.get_for_user(project_id, user_id)
        if not project:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(project, key, value)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def delete(self, project_id: str, user_id: str) -> bool:
        project = await self.get_for_user(project_id, user_id)
        if not project:
            return False
        if project.workspace_path and os.path.exists(project.workspace_path):
            shutil.rmtree(project.workspace_path, ignore_errors=True)
        await self.db.delete(project)
        await self.db.commit()
        return True

    async def update_status(self, project_id: str, status: str, container_id: str | None = None, preview_port: int | None = None) -> None:
        project = await self.get_by_id(project_id)
        if not project:
            return
        project.status = status
        if container_id is not None:
            project.container_id = container_id
        if preview_port is not None:
            project.preview_port = preview_port
        await self.db.commit()
