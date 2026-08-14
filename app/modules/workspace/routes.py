"""Workspace routes: start, stop, status, preview."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.dependencies import RequiredUser
from app.modules.projects.services import ProjectService
from app.modules.workspace.services import WorkspaceService

router = APIRouter(tags=["workspace"])
templates = Jinja2Templates(directory="templates")


@router.post("/api/projects/{project_id}/start")
async def start_workspace(request: Request, user: RequiredUser, project_id: str):
    db = request.state.db
    project_service = ProjectService(db)
    project = await project_service.get_for_user(project_id, user.id)
    if not project:
        from app.common.exceptions import NotFoundError
        raise NotFoundError("Project not found")
    workspace_service = WorkspaceService(project_service)
    result = await workspace_service.start_workspace(project)
    return result


@router.post("/api/projects/{project_id}/stop")
async def stop_workspace(request: Request, user: RequiredUser, project_id: str):
    db = request.state.db
    project_service = ProjectService(db)
    project = await project_service.get_for_user(project_id, user.id)
    if not project:
        from app.common.exceptions import NotFoundError
        raise NotFoundError("Project not found")
    workspace_service = WorkspaceService(project_service)
    result = await workspace_service.stop_workspace(project)
    return result


@router.get("/api/projects/{project_id}/status")
async def workspace_status(request: Request, user: RequiredUser, project_id: str):
    db = request.state.db
    project_service = ProjectService(db)
    project = await project_service.get_for_user(project_id, user.id)
    if not project:
        from app.common.exceptions import NotFoundError
        raise NotFoundError("Project not found")
    workspace_service = WorkspaceService(project_service)
    return await workspace_service.get_status(project)


@router.get("/api/projects/{project_id}/git")
async def git_info(request: Request, user: RequiredUser, project_id: str):
    db = request.state.db
    project_service = ProjectService(db)
    project = await project_service.get_for_user(project_id, user.id)
    if not project:
        from app.common.exceptions import NotFoundError
        raise NotFoundError("Project not found")
    from app.modules.git.services import GitService
    git = GitService(project.workspace_path)
    is_repo = await git.is_repo()
    status = await git.status() if is_repo else None
    return {
        "is_repo": is_repo,
        "status": status.output if status else "",
    }


@router.post("/api/projects/{project_id}/git/init")
async def git_init(request: Request, user: RequiredUser, project_id: str):
    db = request.state.db
    project_service = ProjectService(db)
    project = await project_service.get_for_user(project_id, user.id)
    if not project:
        from app.common.exceptions import NotFoundError
        raise NotFoundError("Project not found")
    from app.modules.git.services import GitService
    git = GitService(project.workspace_path)
    result = await git.init()
    return {"success": result.success, "output": result.output, "error": result.error}


@router.post("/api/projects/{project_id}/git/commit")
async def git_commit(request: Request, user: RequiredUser, project_id: str, message: str = "Update"):
    db = request.state.db
    project_service = ProjectService(db)
    project = await project_service.get_for_user(project_id, user.id)
    if not project:
        from app.common.exceptions import NotFoundError
        raise NotFoundError("Project not found")
    from app.modules.git.services import GitService
    git = GitService(project.workspace_path)
    await git.add()
    result = await git.commit(message)
    return {"success": result.success, "output": result.output, "error": result.error}
