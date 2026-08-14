"""RAG indexer: chunks and indexes project files."""
from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path

from app.common.utils import get_file_language, ignore_patterns
from app.config import settings

logger = logging.getLogger(__name__)

MAX_CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200


def chunk_text(text: str, max_size: int = MAX_CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    if len(text) <= max_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_size
        if end < len(text):
            last_newline = text.rfind("\n", start, end)
            if last_newline > start:
                end = last_newline
        chunks.append(text[start:end])
        start = end - overlap
        if start >= len(text):
            break
    return chunks


def file_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


class RAGIndexer:
    def __init__(self, workspace_path: str):
        self.workspace = workspace_path
        self.rag_enabled = settings.rag_enabled

    def index_project(self) -> list[dict]:
        if not self.rag_enabled:
            return []
        chunks: list[dict] = []
        for dirpath, dirnames, filenames in os.walk(self.workspace):
            dirnames[:] = [d for d in dirnames if not ignore_patterns(os.path.relpath(os.path.join(dirpath, d), self.workspace))]
            for fname in filenames:
                full = os.path.join(dirpath, fname)
                rel = os.path.relpath(full, self.workspace)
                if ignore_patterns(rel):
                    continue
                try:
                    with open(full, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except Exception:
                    continue
                if not content.strip():
                    continue
                file_chunks = chunk_text(content)
                for i, chunk in enumerate(file_chunks):
                    chunks.append({
                        "file_path": rel,
                        "chunk_index": i,
                        "content": chunk,
                        "language": get_file_language(fname),
                        "hash": file_hash(chunk),
                    })
        return chunks

    def index_file(self, rel_path: str) -> list[dict]:
        full = os.path.join(self.workspace, rel_path)
        if not os.path.isfile(full):
            return []
        try:
            with open(full, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return []
        if not content.strip():
            return []
        file_chunks = chunk_text(content)
        return [
            {
                "file_path": rel_path,
                "chunk_index": i,
                "content": chunk,
                "language": get_file_language(rel_path),
                "hash": file_hash(chunk),
            }
            for i, chunk in enumerate(file_chunks)
        ]
