"""File routes."""
from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.dependencies import RequiredUser
from app.modules.files.services import FileService
from app.modules.projects.services import ProjectService

router = APIRouter(prefix="/api/projects/{project_id}/files", tags=["files"])


def _get_file_service(request: Request, user: RequiredUser, project_id: str) -> FileService:
    db = request.state.db
    project_service = ProjectService(db)
    project = project_service.get_for_user_sync(project_id, user.id) if hasattr(project_service, "get_for_user_sync") else None
    return FileService(project.workspace_path) if project else None


class FileWriteRequest(BaseModel):
    path: str
    content: str = ""


class FileActionRequest(BaseModel):
    path: str


class RenameRequest(BaseModel):
    path: str
    new_name: str


class SearchRequest(BaseModel):
    query: str
    path: str = ""


@router.get("/tree")
async def file_tree(request: Request, user: RequiredUser, project_id: str, path: str = ""):
    db = request.state.db
    project = await ProjectService(db).get_for_user(project_id, user.id)
    if not project:
        from app.common.exceptions import NotFoundError
        raise NotFoundError("Project not found")
    service = FileService(project.workspace_path)
    return service.list_tree(path)


@router.get("/read")
async def read_file(request: Request, user: RequiredUser, project_id: str, path: str):
    db = request.state.db
    project = await ProjectService(db).get_for_user(project_id, user.id)
    if not project:
        from app.common.exceptions import NotFoundError
        raise NotFoundError("Project not found")
    service = FileService(project.workspace_path)
    try:
        content = service.read_file(path)
        return {"path": path, "content": content}
    except FileNotFoundError:
        from app.common.exceptions import NotFoundError
        raise NotFoundError("File not found")


@router.post("/write")
async def write_file(request: Request, user: RequiredUser, project_id: str, data: FileWriteRequest):
    db = request.state.db
    project = await ProjectService(db).get_for_user(project_id, user.id)
    if not project:
        from app.common.exceptions import NotFoundError
        raise NotFoundError("Project not found")
    service = FileService(project.workspace_path)
    service.write_file(data.path, data.content)
    return {"ok": True, "path": data.path}


@router.post("/create")
async def create_file(request: Request, user: RequiredUser, project_id: str, data: FileWriteRequest):
    db = request.state.db
    project = await ProjectService(db).get_for_user(project_id, user.id)
    if not project:
        from app.common.exceptions import NotFoundError
        raise NotFoundError("Project not found")
    service = FileService(project.workspace_path)
    service.create_file(data.path, data.content)
    return {"ok": True, "path": data.path}


@router.post("/mkdir")
async def create_dir(request: Request, user: RequiredUser, project_id: str, data: FileActionRequest):
    db = request.state.db
    project = await ProjectService(db).get_for_user(project_id, user.id)
    if not project:
        from app.common.exceptions import NotFoundError
        raise NotFoundError("Project not found")
    service = FileService(project.workspace_path)
    service.create_dir(data.path)
    return {"ok": True}


@router.delete("")
async def delete_file(request: Request, user: RequiredUser, project_id: str, path: str):
    db = request.state.db
    project = await ProjectService(db).get_for_user(project_id, user.id)
    if not project:
        from app.common.exceptions import NotFoundError
        raise NotFoundError("Project not found")
    service = FileService(project.workspace_path)
    deleted = service.delete_file(path)
    if not deleted:
        from app.common.exceptions import NotFoundError
        raise NotFoundError("File not found")
    return {"ok": True}


@router.post("/rename")
async def rename_file(request: Request, user: RequiredUser, project_id: str, data: RenameRequest):
    db = request.state.db
    project = await ProjectService(db).get_for_user(project_id, user.id)
    if not project:
        from app.common.exceptions import NotFoundError
        raise NotFoundError("Project not found")
    service = FileService(project.workspace_path)
    new_path = service.rename(data.path, data.new_name)
    return {"ok": True, "path": new_path}


@router.post("/search")
async def search_files(request: Request, user: RequiredUser, project_id: str, data: SearchRequest):
    db = request.state.db
    project = await ProjectService(db).get_for_user(project_id, user.id)
    if not project:
        from app.common.exceptions import NotFoundError
        raise NotFoundError("Project not found")
    service = FileService(project.workspace_path)
    return service.search_files(data.query, data.path)
