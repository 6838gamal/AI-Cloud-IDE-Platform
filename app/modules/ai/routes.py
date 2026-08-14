"""AI routes: chat endpoint and WebSocket for streaming."""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.dependencies import RequiredUser
from app.modules.ai.agent import AIAgent
from app.modules.ai.services import AIService
from app.modules.files.services import FileService
from app.modules.projects.services import ProjectService
from app.modules.rag.retriever import RAGRetriever
from app.database import async_session_factory

router = APIRouter(tags=["ai"])
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


@router.post("/api/projects/{project_id}/ai/chat")
async def ai_chat(request: Request, user: RequiredUser, project_id: str, data: ChatRequest):
    db = request.state.db
    project_service = ProjectService(db)
    project = await project_service.get_for_user(project_id, user.id)
    if not project:
        from app.common.exceptions import NotFoundError
        raise NotFoundError("Project not found")

    file_service = FileService(project.workspace_path)
    ai_service = AIService()

    rag_retriever = None
    if ai_service.available:
        try:
            rag_retriever = RAGRetriever(db, project.id, file_service)
        except Exception:
            rag_retriever = None

    agent = AIAgent(file_service, ai_service, rag_retriever)

    results: list[dict] = []
    async for chunk in agent.run(data.message, data.history):
        results.append(chunk)
        if chunk.get("type") == "error":
            return {"results": results}

    return {"results": results}


@router.websocket("/ws/ai/{project_id}")
async def ai_ws(websocket: WebSocket, project_id: str):
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

    file_service = FileService(project.workspace_path)
    ai_service = AIService()
    rag_retriever = None
    if ai_service.available:
        try:
            async with async_session_factory() as db:
                rag_retriever = RAGRetriever(db, project.id, file_service)
        except Exception:
            rag_retriever = None

    agent = AIAgent(file_service, ai_service, rag_retriever)

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "chat":
                history = msg.get("history", [])
                async for chunk in agent.run(msg.get("message", ""), history):
                    await websocket.send_json(chunk)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.exception("AI WebSocket error")
        try:
            await websocket.send_json({"type": "error", "data": str(e)})
        except Exception:
            pass
