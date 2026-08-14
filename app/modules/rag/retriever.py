"""RAG retriever: search and rank project context."""
from __future__ import annotations

import logging
import re
from typing import Any

from app.config import settings
from app.modules.files.services import FileService
from app.modules.rag.indexer import RAGIndexer

logger = logging.getLogger(__name__)


class RAGRetriever:
    def __init__(self, db: Any, project_id: str, file_service: FileService):
        self.db = db
        self.project_id = project_id
        self.file_service = file_service
        self.rag_enabled = settings.rag_enabled
        self.top_k = settings.rag_top_k

    @property
    def available(self) -> bool:
        return self.rag_enabled

    async def retrieve(self, query: str) -> str:
        if not self.rag_enabled:
            return ""

        indexer = RAGIndexer(self.file_service.workspace)
        chunks = indexer.index_project()

        if not chunks:
            return ""

        scored = self._score_chunks(chunks, query)
        top = scored[: self.top_k]

        context_parts = []
        for chunk in top:
            context_parts.append(f"--- {chunk['file_path']} ---\n{chunk['content']}\n")
        return "\n".join(context_parts)

    def _score_chunks(self, chunks: list[dict], query: str) -> list[dict]:
        query_terms = [t.lower() for t in re.findall(r"\w+", query)]
        if not query_terms:
            return chunks

        scored: list[tuple[float, dict]] = []
        for chunk in chunks:
            content_lower = chunk["content"].lower()
            score = 0.0
            for term in query_terms:
                count = content_lower.count(term)
                score += count
                if term in chunk["file_path"].lower():
                    score += 2
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored]
