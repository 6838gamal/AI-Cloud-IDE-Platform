"""Custom exceptions and handlers."""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates


class AppError(Exception):
    status_code = 400
    message = "An error occurred"

    def __init__(self, message: str | None = None, status_code: int | None = None):
        if message:
            self.message = message
        if status_code:
            self.status_code = status_code
        super().__init__(self.message)


class AuthenticationRequiredError(AppError):
    status_code = 401
    message = "Authentication required"


class NotFoundError(AppError):
    status_code = 404
    message = "Not found"


class ForbiddenError(AppError):
    status_code = 403
    message = "Forbidden"


class ValidationError(AppError):
    status_code = 422
    message = "Validation error"


class ServiceNotConfiguredError(AppError):
    status_code = 503
    message = "Service not configured"


def register_exception_handlers(app, templates: Jinja2Templates) -> None:
    @app.exception_handler(AuthenticationRequiredError)
    async def _auth_required(request: Request, exc: AuthenticationRequiredError):
        if request.url.path.startswith("/api/"):
            return JSONResponse({"error": exc.message}, status_code=exc.status_code)
        return RedirectResponse(url="/auth/login", status_code=302)

    @app.exception_handler(NotFoundError)
    async def _not_found(request: Request, exc: NotFoundError):
        if request.url.path.startswith("/api/"):
            return JSONResponse({"error": exc.message}, status_code=exc.status_code)
        return JSONResponse({"error": exc.message}, status_code=exc.status_code)

    @app.exception_handler(ForbiddenError)
    async def _forbidden(request: Request, exc: ForbiddenError):
        return JSONResponse({"error": exc.message}, status_code=exc.status_code)

    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError):
        return JSONResponse({"error": exc.message}, status_code=exc.status_code)
