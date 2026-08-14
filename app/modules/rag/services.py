"""RAG service: orchestrate indexing and retrieval."""
from __future__ import annotations

from app.modules.files.services import FileService
from app.modules.rag.indexer import RAGIndexer
from app.modules.rag.retriever import RAGRetriever


class RAGService:
    def __init__(self, workspace_path: str):
        self.indexer = RAGIndexer(workspace_path)

    def index_project(self) -> dict:
        chunks = self.indexer.index_project()
        return {"indexed": len(chunks), "chunks": chunks}

    def index_file(self, rel_path: str) -> dict:
        chunks = self.indexer.index_file(rel_path)
        return {"indexed": len(chunks), "file": rel_path, "chunks": chunks}
