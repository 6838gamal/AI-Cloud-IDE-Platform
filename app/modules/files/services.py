"""File management service."""
from __future__ import annotations

import os
from pathlib import Path

from app.common.utils import get_file_language, human_size, ignore_patterns, safe_join


class FileService:
    def __init__(self, workspace_path: str):
        self.workspace = workspace_path

    def _safe(self, rel_path: str) -> str:
        return safe_join(self.workspace, rel_path)

    def list_tree(self, path: str = "") -> dict:
        root = self._safe(path)
        if not os.path.isdir(root):
            return {}
        return self._build_tree(root, self.workspace)

    def _build_tree(self, current: str, base: str) -> dict:
        result = {"name": os.path.basename(current) or "/", "path": os.path.relpath(current, base), "type": "dir", "children": []}
        try:
            entries = sorted(os.listdir(current), key=lambda x: (not os.path.isdir(os.path.join(current, x)), x.lower()))
        except PermissionError:
            return result
        for entry in entries:
            full = os.path.join(current, entry)
            rel = os.path.relpath(full, base)
            if ignore_patterns(rel):
                continue
            if os.path.isdir(full):
                result["children"].append(self._build_tree(full, base))
            else:
                size = os.path.getsize(full)
                result["children"].append({
                    "name": entry,
                    "path": rel,
                    "type": "file",
                    "size": size,
                    "size_human": human_size(size),
                    "language": get_file_language(entry),
                })
        return result

    def read_file(self, rel_path: str) -> str:
        full = self._safe(rel_path)
        if not os.path.isfile(full):
            raise FileNotFoundError(f"File not found: {rel_path}")
        with open(full, "r", encoding="utf-8") as f:
            return f.read()

    def write_file(self, rel_path: str, content: str) -> None:
        full = self._safe(rel_path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)

    def delete_file(self, rel_path: str) -> bool:
        full = self._safe(rel_path)
        if os.path.isfile(full):
            os.remove(full)
            return True
        if os.path.isdir(full):
            import shutil
            shutil.rmtree(full)
            return True
        return False

    def create_file(self, rel_path: str, content: str = "") -> None:
        self.write_file(rel_path, content)

    def create_dir(self, rel_path: str) -> None:
        full = self._safe(rel_path)
        os.makedirs(full, exist_ok=True)

    def rename(self, rel_path: str, new_name: str) -> str:
        full = self._safe(rel_path)
        parent = os.path.dirname(full)
        new_path = safe_join(parent, new_name)
        os.rename(full, new_path)
        return os.path.relpath(new_path, self.workspace)

    def search_files(self, query: str, path: str = "") -> list[dict]:
        root = self._safe(path)
        results = []
        query_lower = query.lower()
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not ignore_patterns(os.path.relpath(os.path.join(dirpath, d), self.workspace))]
            for fname in filenames:
                full = os.path.join(dirpath, fname)
                rel = os.path.relpath(full, self.workspace)
                if ignore_patterns(rel):
                    continue
                if query_lower in fname.lower():
                    results.append({"path": rel, "match": "filename"})
                    continue
                try:
                    with open(full, "r", encoding="utf-8", errors="ignore") as f:
                        for i, line in enumerate(f, 1):
                            if query_lower in line.lower():
                                results.append({"path": rel, "line": i, "match": line.strip()[:200]})
                                break
                except Exception:
                    pass
        return results[:50]
