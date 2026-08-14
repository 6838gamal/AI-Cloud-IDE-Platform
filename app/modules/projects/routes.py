"""Project routes."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.dependencies import CurrentUser, RequiredUser
from app.modules.projects.schemas import ProjectCreate, ProjectUpdate
from app.modules.projects.services import ProjectService

router = APIRouter(tags=["projects"])
templates = Jinja2Templates(directory="templates")


@router.get("/dashboard")
async def dashboard(request: Request, user: RequiredUser):
    db = request.state.db
    service = ProjectService(db)
    projects = await service.list_for_user(user.id)
    return templates.TemplateResponse("dashboard/index.html", {
        "request": request,
        "user": user,
        "projects": projects,
    })


@router.post("/api/projects")
async def create_project(request: Request, user: RequiredUser, data: ProjectCreate):
    db = request.state.db
    service = ProjectService(db)
    project = await service.create(user.id, data)
    return {
        "id": project.id,
        "name": project.name,
        "slug": project.slug,
        "project_type": project.project_type,
        "status": project.status,
    }


@router.get("/api/projects")
async def list_projects(request: Request, user: RequiredUser):
    db = request.state.db
    service = ProjectService(db)
    projects = await service.list_for_user(user.id)
    return [
        {
            "id": p.id,
            "name": p.name,
            "slug": p.slug,
            "description": p.description,
            "project_type": p.project_type,
            "status": p.status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in projects
    ]


@router.patch("/api/projects/{project_id}")
async def update_project(request: Request, user: RequiredUser, project_id: str, data: ProjectUpdate):
    db = request.state.db
    service = ProjectService(db)
    project = await service.update(project_id, user.id, data)
    if not project:
        from app.common.exceptions import NotFoundError
        raise NotFoundError("Project not found")
    return {"id": project.id, "name": project.name, "description": project.description}


@router.delete("/api/projects/{project_id}")
async def delete_project(request: Request, user: RequiredUser, project_id: str):
    db = request.state.db
    service = ProjectService(db)
    deleted = await service.delete(project_id, user.id)
    if not deleted:
        from app.common.exceptions import NotFoundError
        raise NotFoundError("Project not found")
    return {"ok": True}


@router.get("/workspace/{project_id}")
async def workspace(request: Request, user: RequiredUser, project_id: str):
    db = request.state.db
    service = ProjectService(db)
    project = await service.get_for_user(project_id, user.id)
    if not project:
        from app.common.exceptions import NotFoundError
        raise NotFoundError("Project not found")
    return templates.TemplateResponse("workspace/index.html", {
        "request": request,
        "user": user,
        "project": project,
    })
