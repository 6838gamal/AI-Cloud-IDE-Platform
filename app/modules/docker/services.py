"""Docker service: container lifecycle for workspaces."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ContainerResult:
    success: bool
    container_id: str = ""
    output: str = ""
    error: str = ""


class DockerService:
    def __init__(self):
        self.enabled = settings.docker_enabled

    async def _run(self, *args: str) -> tuple[str, str, int]:
        proc = await asyncio.create_subprocess_exec(
            "docker", *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace"), proc.returncode or 0

    async def is_available(self) -> bool:
        if not self.enabled:
            return False
        try:
            out, _, code = await self._run("info")
            return code == 0
        except Exception:
            return False

    async def build_image(self, dockerfile_path: str, tag: str, context: str = ".") -> ContainerResult:
        out, err, code = await self._run("build", "-f", dockerfile_path, "-t", tag, context)
        return ContainerResult(success=code == 0, output=out, error=err)

    async def create_container(
        self,
        image: str,
        workspace_path: str,
        name: str,
        ports: dict[int, int] | None = None,
        env: dict[str, str] | None = None,
    ) -> ContainerResult:
        args = ["create", "--name", name, "-w", "/workspace"]
        if ports:
            for host_port, container_port in ports.items():
                args.extend(["-p", f"{host_port}:{container_port}"])
        if env:
            for k, v in env.items():
                args.extend(["-e", f"{k}={v}"])
        args.extend(["-v", f"{workspace_path}:/workspace", image])
        out, err, code = await self._run(*args)
        container_id = out.strip()
        return ContainerResult(success=code == 0, container_id=container_id, output=out, error=err)

    async def start_container(self, container_id: str) -> ContainerResult:
        out, err, code = await self._run("start", container_id)
        return ContainerResult(success=code == 0, container_id=container_id, output=out, error=err)

    async def stop_container(self, container_id: str) -> ContainerResult:
        out, err, code = await self._run("stop", container_id)
        return ContainerResult(success=code == 0, container_id=container_id, output=out, error=err)

    async def remove_container(self, container_id: str, force: bool = False) -> ContainerResult:
        args = ["rm", container_id]
        if force:
            args.insert(1, "-f")
        out, err, code = await self._run(*args)
        return ContainerResult(success=code == 0, container_id=container_id, output=out, error=err)

    async def exec_in_container(self, container_id: str, *cmd: str) -> ContainerResult:
        out, err, code = await self._run("exec", container_id, *cmd)
        return ContainerResult(success=code == 0, output=out, error=err)

    async def get_container_status(self, container_id: str) -> str:
        out, _, code = await self._run("inspect", "--format", "{{.State.Status}}", container_id)
        if code != 0:
            return "not_found"
        return out.strip()
