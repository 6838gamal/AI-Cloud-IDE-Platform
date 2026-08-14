"""Shared utility functions."""
from __future__ import annotations

import os
import re
from pathlib import Path

SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9._\-/]+$")


def safe_join(base: str, *paths: str) -> str:
    """Safely join paths, preventing path traversal."""
    base_path = Path(base).resolve()
    result = (base_path.joinpath(*paths)).resolve()
    if not str(result).startswith(str(base_path)):
        raise ValueError("Path traversal detected")
    return str(result)


def is_safe_name(name: str) -> bool:
    return bool(SAFE_NAME_RE.match(name)) and ".." not in name


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text)


def human_size(bytes_size: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} TB"


def get_file_language(filename: str) -> str:
    ext_map = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".html": "html", ".css": "css", ".json": "json",
        ".md": "markdown", ".yml": "yaml", ".yaml": "yaml",
        ".dart": "dart", ".sql": "sql", ".sh": "shell",
        ".txt": "text", ".toml": "toml", ".cfg": "ini",
        ".ini": "ini", ".env": "ini", ".xml": "xml",
    }
    ext = Path(filename).suffix.lower()
    return ext_map.get(ext, "text")


def ignore_patterns(path: str) -> bool:
    """Return True if path should be ignored in file tree / indexing."""
    parts = Path(path).parts
    ignored_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv",
                    ".idea", ".vscode", "build", ".dart_tool", ".gradle"}
    return any(p in ignored_dirs for p in parts)
