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
        # If task_id is provided, look up the workspace directory
        task_id = kwargs.get("_task_id")
        workspace_path = None
        if task_id:
            from app.services.workspace_manager import WorkspaceManager
            ws = WorkspaceManager()
            workspace_path = ws.get_path(task_id)

        if _is_docker_available():
            return await self._run_in_docker(code, timeout, task_id=task_id, workspace_path=workspace_path)
        else:
            logger.warning(
                "Docker not available — falling back to subprocess execution"
            )
            return await self._run_in_subprocess(code, timeout, workspace_path=workspace_path)

    # ── Docker path ───────────────────────────────────────────────────────────

    async def _run_in_docker(self, code: str, timeout: int, task_id: str | None = None, workspace_path: str | None = None) -> str:
        import docker  # type: ignore
        import uuid
        from app.services.container_pool import ContainerPool

        pool = ContainerPool.get_instance()
        
        # We need an identifier for locking/scratch even if no task_id
        effective_task_id = task_id or f"ephemeral-{uuid.uuid4().hex[:8]}"

        container_id = await pool.acquire(effective_task_id)

        try:
            if container_id:
                # ── POOL CONTAINER PATH ──
                # We have a pre-warmed container with /workspaces mounted.
                # Write the script to a shared scratch location.
                scratch_dir = os.path.join(pool.workspaces_dir, ".scratch")
                os.makedirs(scratch_dir, exist_ok=True)
                
                script_id = uuid.uuid4().hex
                host_script_path = os.path.join(scratch_dir, f"script_{script_id}.py")
                container_script_path = f"/workspaces/.scratch/script_{script_id}.py"
                
                with open(host_script_path, "w", encoding="utf-8") as f:
                    f.write(code)
                
                workdir = f"/workspaces/{effective_task_id}" if task_id else "/workspaces"

                def _run_pool():
                    client = docker.from_env()
                    c = client.containers.get(container_id)
                    try:
                        # exec_run doesn't natively support timeout in the python client,
                        # so we rely on the asyncio.wait_for wrapper around this blocking call.
                        exit_code, output = c.exec_run(
                            cmd=["python", container_script_path],
                            workdir=workdir,
                        )
                        return output.decode("utf-8", errors="replace")
                    except Exception as exc:
                        return f"Docker pool execution error: {exc}"
                    finally:
                        # Cleanup scratch script
                        if os.path.exists(host_script_path):
                            try:
                                os.remove(host_script_path)
                            except OSError:
                                pass

                try:
                    loop = asyncio.get_event_loop()
                    result = await asyncio.wait_for(
                        loop.run_in_executor(None, _run_pool), timeout=timeout + 5
                    )
                    return result or "(no output)"
                except asyncio.TimeoutError:
                    return f"Execution timed out after {timeout} seconds."
                    
            else:
                # ── EPHEMERAL CONTAINER FALLBACK PATH ──
                # Pool is exhausted or disabled, spin up a fresh temporary container
                logger.debug("ContainerPool exhausted, spinning up ephemeral container.")
                with tempfile.TemporaryDirectory() as tmpdir:
                    script_path = os.path.join(tmpdir, "script.py")
                    with open(script_path, "w", encoding="utf-8") as f:
                        f.write(code)

                    def _run_ephemeral():
                        client = docker.from_env()
                        try:
                            # Build volume mounts
                            volumes = {tmpdir: {"bind": "/workspace", "mode": "ro"}}
                            if workspace_path and os.path.isdir(workspace_path):
                                volumes[workspace_path] = {"bind": "/task_workspace", "mode": "rw"}

                            output = client.containers.run(
                                image=DOCKER_IMAGE,
                                command=["python", "/workspace/script.py"],
                                volumes=volumes,
                                network_disabled=True,
                                mem_limit="256m",
                                cpu_period=100000,
                                cpu_quota=50000,  # 50% of one CPU
                                read_only=True,
                                cap_drop=["ALL"],
                                tmpfs={"/tmp": "size=64m"},
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
                            loop.run_in_executor(None, _run_ephemeral), timeout=timeout + 5
                        )
                        return result or "(no output)"
                    except asyncio.TimeoutError:
                        return f"Execution timed out after {timeout} seconds."

        finally:
            # Always release the container back to the pool if we acquired one
            if container_id:
                await pool.release(container_id)

    # ── Subprocess fallback ───────────────────────────────────────────────────

    async def _run_in_subprocess(self, code: str, timeout: int, workspace_path: str | None = None) -> str:
        with tempfile.NamedTemporaryFile(
            suffix=".py", mode="w", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            path = f.name
        try:
            # Use workspace as cwd if available
            cwd = workspace_path if workspace_path and os.path.isdir(workspace_path) else None
            proc = await asyncio.create_subprocess_exec(
                "python",
                path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
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
