"""AI Agent: orchestrates LLM + tools to modify projects."""
from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator

from app.modules.ai.services import AIService
from app.modules.ai.tools import TOOL_DEFINITIONS, execute_tool
from app.modules.files.services import FileService
from app.modules.rag.retriever import RAGRetriever

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 10

SYSTEM_PROMPT = """You are an AI coding agent working inside a cloud IDE platform.
You help users build and modify their projects by using tools.

When a user asks you to:
- Create a project: scaffold the appropriate files
- Add a feature: read relevant files, understand the structure, then make changes
- Fix a bug: read the relevant code, identify the issue, fix it
- Add dependencies: update requirements.txt or pubspec.yaml

Always read files before editing. Use search_files to find relevant code.
Make targeted edits using edit_file. For new files, use write_file.
Show what you changed and explain briefly."""

RAG_SYSTEM_PROMPT = """You have access to project context retrieved via RAG.
Use this context to understand the project structure before making changes."""


class AIAgent:
    def __init__(self, file_service: FileService, ai_service: AIService, rag_retriever: RAGRetriever | None = None):
        self.file_service = file_service
        self.ai = ai_service
        self.rag = rag_retriever

    async def run(self, user_message: str, history: list[dict] | None = None) -> AsyncGenerator[dict, None]:
        if not self.ai.available:
            yield {"type": "error", "data": "AI is not configured. Set AI_PROVIDER and AI_API_KEY in settings."}
            return

        messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]

        if self.rag and self.rag.available:
            context = await self.rag.retrieve(user_message)
            if context:
                messages.append({"role": "system", "content": f"{RAG_SYSTEM_PROMPT}\n\nProject context:\n{context}"})

        if history:
            messages.extend(history)

        messages.append({"role": "user", "content": user_message})

        for iteration in range(MAX_ITERATIONS):
            response = await self.ai.chat(messages, TOOL_DEFINITIONS)

            if "error" in response:
                yield {"type": "error", "data": response["error"]}
                return

            choice = response.get("choices", [{}])[0]
            message = choice.get("message", {})

            if message.get("content"):
                yield {"type": "message", "data": message["content"]}

            tool_calls = message.get("tool_calls", [])
            if not tool_calls:
                return

            messages.append(message)

            for tc in tool_calls:
                func = tc.get("function", {})
                tool_name = func.get("name", "")
                try:
                    arguments = json.loads(func.get("arguments", "{}"))
                except json.JSONDecodeError:
                    arguments = {}

                yield {"type": "tool_call", "data": {"name": tool_name, "arguments": arguments}}

                result = await execute_tool(tool_name, arguments, self.file_service)

                yield {"type": "tool_result", "data": {"name": tool_name, "result": result[:2000]}}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": result,
                })

        yield {"type": "error", "data": "Max iterations reached"}
