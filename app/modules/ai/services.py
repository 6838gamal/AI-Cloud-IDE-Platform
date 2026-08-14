"""AI service: provider abstraction for LLM calls."""
from __future__ import annotations

import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self):
        self.provider = settings.ai_provider.lower() if settings.ai_provider else ""
        self.api_key = settings.ai_api_key
        self.model = settings.ai_model
        self.base_url = settings.ai_base_url

    @property
    def available(self) -> bool:
        return settings.ai_configured

    async def chat(self, messages: list[dict[str, str]], tools: list[dict] | None = None) -> dict[str, Any]:
        if not self.available:
            return {"error": "AI is not configured. Set AI_PROVIDER and AI_API_KEY."}

        if self.provider in ("openai", "openai-compatible"):
            return await self._call_openai(messages, tools)
        return {"error": f"Unsupported AI provider: {self.provider}"}

    async def _call_openai(self, messages: list[dict[str, str]], tools: list[dict] | None = None) -> dict[str, Any]:
        import httpx

        base = self.base_url or "https://api.openai.com/v1"
        url = f"{base}/chat/completions"
        payload: dict[str, Any] = {
            "model": self.model or "gpt-4o",
            "messages": messages,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if resp.status_code != 200:
                return {"error": f"AI API error: {resp.status_code} {resp.text}"}
            data = resp.json()
            return data
