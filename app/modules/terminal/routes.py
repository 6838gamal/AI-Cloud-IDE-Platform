"""Terminal WebSocket routes."""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.dependencies import require_user_ws
from app.modules.docker.services import DockerService
from app.modules.projects.services import ProjectService
from app.modules.terminal.services import TerminalService
from app.database import async_session_factory

router = APIRouter(tags=["terminal"])
logger = logging.getLogger(__name__)


@router.websocket("/ws/terminal/{project_id}")
async def terminal_ws(websocket: WebSocket, project_id: str):
    await websocket.accept()

    token = websocket.query_params.get("token")
    if not token:
        await websocket.send_json({"type": "error", "data": "No token"})
        await websocket.close()
        return

    async with async_session_factory() as db:
        from app.modules.auth.services import AuthService
        auth_service = AuthService(db)
        user_id = await auth_service.get_session_user_id(token)
        if not user_id:
            await websocket.send_json({"type": "error", "data": "Invalid session"})
            await websocket.close()
            return

        project_service = ProjectService(db)
        project = await project_service.get_for_user(project_id, user_id)
        if not project:
            await websocket.send_json({"type": "error", "data": "Project not found"})
            await websocket.close()
            return

    if not project.container_id:
        await websocket.send_json({"type": "error", "data": "Container not running. Start the workspace first."})
        await websocket.close()
        return

    docker_service = DockerService()
    terminal_service = TerminalService(docker_service)

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "command":
                cmd = msg.get("cmd", "")
                if not cmd:
                    continue
                import shlex
                parts = shlex.split(cmd)
                await websocket.send_json({"type": "stdout", "data": f"$ {cmd}\n"})
                async for chunk in terminal_service.run_command_stream(project.container_id, *parts):
                    await websocket.send_json(chunk)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.exception("Terminal WebSocket error")
        try:
            await websocket.send_json({"type": "error", "data": str(e)})
        except Exception:
            pass
