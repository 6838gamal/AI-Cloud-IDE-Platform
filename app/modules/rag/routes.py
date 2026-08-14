"""RAG routes."""
from __future__ import annotations

from fastapi import APIRouter, Request

from app.dependencies import RequiredUser
from app.modules.files.services import FileService
from app.modules.projects.services import ProjectService
from app.modules.rag.services import RAGService

router = APIRouter(prefix="/api/projects/{project_id}/rag", tags=["rag"])


@router.post("/index")
async def index_project(request: Request, user: RequiredUser, project_id: str):
    db = request.state.db
    project = await ProjectService(db).get_for_user(project_id, user.id)
    if not project:
        from app.common.exceptions import NotFoundError
        raise NotFoundError("Project not found")
    service = RAGService(project.workspace_path)
    result = service.index_project()
    return {"indexed": result["indexed"]}


@router.post("/index-file")
async def index_file(request: Request, user: RequiredUser, project_id: str, path: str):
    db = request.state.db
    project = await ProjectService(db).get_for_user(project_id, user.id)
    if not project:
        from app.common.exceptions import NotFoundError
        raise NotFoundError("Project not found")
    service = RAGService(project.workspace_path)
    result = service.index_file(path)
    return {"indexed": result["indexed"], "file": path}
