"""Git service: basic git operations on a workspace."""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass


@dataclass
class GitResult:
    success: bool
    output: str
    error: str
    exit_code: int


class GitService:
    def __init__(self, workspace_path: str):
        self.workspace = workspace_path

    async def _run(self, *args: str) -> GitResult:
        proc = await asyncio.create_subprocess_exec(
            "git", *args,
            cwd=self.workspace,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return GitResult(
            success=proc.returncode == 0,
            output=stdout.decode("utf-8", errors="replace"),
            error=stderr.decode("utf-8", errors="replace"),
            exit_code=proc.returncode or 0,
        )

    async def init(self) -> GitResult:
        return await self._run("init")

    async def status(self) -> GitResult:
        return await self._run("status", "--porcelain")

    async def diff(self) -> GitResult:
        return await self._run("diff")

    async def add(self, paths: list[str] | None = None) -> GitResult:
        if paths:
            return await self._run("add", *paths)
        return await self._run("add", "-A")

    async def commit(self, message: str) -> GitResult:
        return await self._run("commit", "-m", message)

    async def branch(self) -> GitResult:
        return await self._run("branch")

    async def checkout(self, branch: str) -> GitResult:
        return await self._run("checkout", branch)

    async def log(self, limit: int = 20) -> GitResult:
        return await self._run("log", f"--max-count={limit}", "--oneline")

    async def is_repo(self) -> bool:
        git_dir = os.path.join(self.workspace, ".git")
        return os.path.isdir(git_dir)

    async def ensure_repo(self) -> None:
        if not await self.is_repo():
            await self.init()
