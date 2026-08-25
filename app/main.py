"""Main FastAPI application."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
#from fastapi.middleware.sessions import SessionMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware

from app.common.exceptions import register_exception_handlers
from app.config import settings
from app.database import async_session_factory, init_db
from app.modules.auth.services import AuthService

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.db = None
        request.state.user = None

        public_paths = ("/auth", "/app/static", "/api/health", "/favicon.ico")
        if any(request.url.path.startswith(p) for p in public_paths):
            return await call_next(request)

        token = request.cookies.get(settings.session_cookie_name)
        if not token:
            if request.url.path.startswith("/api/"):
                return await call_next(request)
            return RedirectResponse(url="/auth/login", status_code=302)

        db = async_session_factory()
        try:
            auth_service = AuthService(db)
            user_id = await auth_service.get_session_user_id(token)
            if not user_id:
                await db.close()
                response = RedirectResponse(url="/auth/login", status_code=302)
                response.delete_cookie(settings.session_cookie_name)
                return response

            from app.modules.users.services import UserService
            user = await UserService(db).get_by_id(user_id)
            request.state.user = user
            request.state.db = db
            response = await call_next(request)
            return response
        except Exception:
            await db.rollback()
            raise
        finally:
            await db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    for issue in settings.warn_insecure_defaults():
        logger.warning("PRODUCTION WARNING: %s", issue)

    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error("Failed to initialize database: %s", e)

    Path(settings.workspace_root).mkdir(parents=True, exist_ok=True)
    logger.info("Workspace root: %s", settings.workspace_root)
    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)
app.add_middleware(AuthMiddleware)

app.mount("static", StaticFiles(directory="/app/static"), name="static")

templates = Jinja2Templates(directory="/app/templates")
templates.env.globals["app_name"] = settings.app_name
templates.env.globals["default_language"] = settings.default_language
templates.env.globals["default_theme"] = settings.default_theme

register_exception_handlers(app, templates)

from app.modules.ai.routes import router as ai_router
from app.modules.auth.routes import router as auth_router
from app.modules.files.routes import router as files_router
from app.modules.projects.routes import router as projects_router
from app.modules.rag.routes import router as rag_router
from app.modules.terminal.routes import router as terminal_router
from app.modules.users.routes import router as users_router
from app.modules.workspace.routes import router as workspace_router

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(projects_router)
app.include_router(files_router)
app.include_router(workspace_router)
app.include_router(ai_router)
app.include_router(rag_router)
app.include_router(terminal_router)


@app.get("/")
async def root():
    return RedirectResponse(url="/dashboard", status_code=302)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "google_configured": settings.google_configured,
        "ai_configured": settings.ai_configured,
        "rag_enabled": settings.rag_enabled,
        "docker_enabled": settings.docker_enabled,
    }


@app.get("/api/services/status")
async def services_status(request: Request):
    from app.modules.docker.services import DockerService
    docker = DockerService()
    docker_available = await docker.is_available() if settings.docker_enabled else False
    return {
        "google": {"configured": settings.google_configured, "available": settings.google_configured},
        "ai": {"configured": settings.ai_configured, "available": settings.ai_configured},
        "rag": {"enabled": settings.rag_enabled, "available": settings.rag_enabled},
        "docker": {"enabled": settings.docker_enabled, "available": docker_available},
    }
