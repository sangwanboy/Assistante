"""DockerCodeExecutorTool: runs Python code inside an isolated Docker container.

Falls back to the subprocess-based CodeExecutorTool automatically when Docker
is not available on the host machine.
"""
from __future__ import annotations

import asyncio
import logging
import tempfile
import os

from app.tools.base import BaseTool

logger = logging.getLogger(__name__)

DOCKER_IMAGE = "python:3.12-slim"
TIMEOUT_SECONDS = 30


def _is_docker_available() -> bool:
    """Return True if the Docker daemon is reachable on this machine."""
    try:
        import docker  # type: ignore
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


class DockerCodeExecutorTool(BaseTool):
    """Executes Python code in a fully isolated Docker container.

    Each execution spins up a fresh container, copies the script in via a
    temporary bind-mount, runs it with a hard timeout, and deletes the
    container.  Falls back to subprocess execution when Docker is unavailable.
    """

    @property
    def name(self) -> str:
        return "execute_code_sandboxed"

    @property
    def description(self) -> str:
        return (
            "Execute Python code in a fully isolated Docker container sandbox. "
            "The container has no network access, no access to the host filesystem, "
            "and is destroyed after execution.  Safer than the basic code executor. "
            "Falls back to subprocess if Docker is unavailable."
        )

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute",
                },
                "timeout": {
                    "type": "integer",
                    "description": f"Max execution time in seconds (default {TIMEOUT_SECONDS})",
                    "default": TIMEOUT_SECONDS,
                },
            },
            "required": ["code"],
        }

    async def execute(self, code: str, timeout: int = TIMEOUT_SECONDS, **kwargs) -> str:
        if _is_docker_available():
            return await self._run_in_docker(code, timeout)
        else:
            logger.warning(
                "Docker not available — falling back to subprocess execution"
            )
            return await self._run_in_subprocess(code, timeout)

    # ── Docker path ───────────────────────────────────────────────────────────

    async def _run_in_docker(self, code: str, timeout: int) -> str:
        import docker  # type: ignore

        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = os.path.join(tmpdir, "script.py")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code)

            def _run():
                client = docker.from_env()
                try:
                    output = client.containers.run(
                        image=DOCKER_IMAGE,
                        command=["python", "/workspace/script.py"],
                        volumes={tmpdir: {"bind": "/workspace", "mode": "ro"}},
                        network_disabled=True,
                        mem_limit="256m",
                        cpu_period=100000,
                        cpu_quota=50000,  # 50% of one CPU
                        remove=True,
                        stdout=True,
                        stderr=True,
                        timeout=timeout,
                    )
                    return output.decode("utf-8", errors="replace")
                except docker.errors.ContainerError as e:
                    return f"Container error:\n{e.stderr.decode('utf-8', errors='replace') if e.stderr else str(e)}"
                except Exception as exc:
                    return f"Docker execution error: {exc}"

            try:
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, _run), timeout=timeout + 5
                )
                return result or "(no output)"
            except asyncio.TimeoutError:
                return f"Execution timed out after {timeout} seconds."

    # ── Subprocess fallback ───────────────────────────────────────────────────

    async def _run_in_subprocess(self, code: str, timeout: int) -> str:
        with tempfile.NamedTemporaryFile(
            suffix=".py", mode="w", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            path = f.name
        try:
            proc = await asyncio.create_subprocess_exec(
                "python",
                path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                return f"Execution timed out after {timeout} seconds."
            output = stdout.decode("utf-8", errors="replace")
            err = stderr.decode("utf-8", errors="replace")
            if err:
                output += f"\n[stderr]\n{err}"
            return output or "(no output)"
        finally:
            os.unlink(path)
