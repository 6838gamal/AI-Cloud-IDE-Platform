"""Terminal service: execute commands in workspace container."""
from __future__ import annotations

import asyncio
import logging

from app.modules.docker.services import DockerService

logger = logging.getLogger(__name__)


class TerminalService:
    def __init__(self, docker_service: DockerService):
        self.docker = docker_service

    async def run_command(self, container_id: str, cmd: list[str]) -> dict:
        result = await self.docker.exec_in_container(container_id, *cmd)
        return {
            "output": result.output,
            "error": result.error,
            "success": result.success,
        }

    async def run_command_stream(self, container_id: str, cmd: list[str]):
        """Async generator yielding output lines."""
        proc = await asyncio.create_subprocess_exec(
            "docker", "exec", container_id, *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        assert proc.stdout is not None
        async for line in proc.stdout:
            yield {"type": "stdout", "data": line.decode("utf-8", errors="replace")}
        await proc.wait()
        yield {"type": "exit", "code": proc.returncode}
