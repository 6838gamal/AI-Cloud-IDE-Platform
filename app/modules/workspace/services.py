"""Workspace service: orchestrates project lifecycle (build, run, stop)."""
from __future__ import annotations

import logging

from app.modules.docker.services import DockerService
from app.modules.projects.models import Project
from app.modules.projects.services import ProjectService

logger = logging.getLogger(__name__)


class WorkspaceService:
    def __init__(self, project_service: ProjectService):
        self.project_service = project_service
        self.docker = DockerService()

    async def start_workspace(self, project: Project) -> dict:
        if not await self.docker.is_available():
            return {"success": False, "error": "Docker is not available"}

        await self.project_service.update_status(project.id, "building")

        image = self._get_image(project.project_type)
        container_name = f"workspace-{project.id}"

        if project.container_id:
            status = await self.docker.get_container_status(project.container_id)
            if status == "running":
                await self.project_service.update_status(project.id, "running")
                return {"success": True, "message": "Already running", "container_id": project.container_id}

        result = await self.docker.create_container(
            image=image,
            workspace_path=project.workspace_path,
            name=container_name,
        )
        if not result.success:
            await self.project_service.update_status(project.id, "error")
            return {"success": False, "error": result.error}

        start_result = await self.docker.start_container(result.container_id)
        if not start_result.success:
            await self.project_service.update_status(project.id, "error")
            return {"success": False, "error": start_result.error}

        await self.project_service.update_status(project.id, "running", container_id=result.container_id)
        return {"success": True, "container_id": result.container_id}

    async def stop_workspace(self, project: Project) -> dict:
        if not project.container_id:
            return {"success": True, "message": "Not running"}
        result = await self.docker.stop_container(project.container_id)
        await self.docker.remove_container(project.container_id, force=True)
        await self.project_service.update_status(project.id, "stopped", container_id=None)
        return {"success": result.success}

    async def get_status(self, project: Project) -> dict:
        if not project.container_id:
            return {"status": project.status}
        container_status = await self.docker.get_container_status(project.container_id)
        return {"status": project.status, "container": container_status}

    def _get_image(self, project_type: str) -> str:
        image_map = {
            "python": "codeforge-python:latest",
            "fastapi": "codeforge-python:latest",
            "flask": "codeforge-python:latest",
            "django": "codeforge-python:latest",
            "streamlit": "codeforge-python:latest",
            "flutter": "codeforge-flutter:latest",
        }
        return image_map.get(project_type, "codeforge-python:latest")
