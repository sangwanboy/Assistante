"""Workspace Tools — allow agents to read/write files within their task workspace.

These tools are automatically available during autonomous execution loops.
They provide a sandboxed filesystem where agents can store intermediate
results, code, data, and outputs.
"""

import json
import asyncio
import logging
from app.tools.base import BaseTool
from app.services.workspace_manager import WorkspaceManager

logger = logging.getLogger(__name__)

_workspace_mgr = WorkspaceManager()


class WorkspaceWriteTool(BaseTool):
    """Write a file to the current task's workspace."""

    @property
    def name(self) -> str:
        return "workspace_write"

    @property
    def description(self) -> str:
        return (
            "Write a file to your task workspace. The workspace is a persistent "
            "sandboxed directory that survives across tool calls. Use this to save "
            "code, data, intermediate results, or outputs. Files written here can be "
            "read back with workspace_read or listed with workspace_list."
        )

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Relative path within the workspace (e.g. 'output.txt', 'src/main.py')",
                },
                "content": {
                    "type": "string",
                    "description": "The file content to write",
                },
            },
            "required": ["file_path", "content"],
        }

    async def execute(self, file_path: str, content: str, **kwargs) -> str:
        task_id = kwargs.get("_task_id")
        if not task_id:
            return "Error: No active task workspace. This tool is only available during autonomous task execution."
        try:
            abs_path = _workspace_mgr.write_file(task_id, file_path, content)
            size = len(content.encode("utf-8"))
            return json.dumps({
                "status": "success",
                "file": file_path,
                "size_bytes": size,
                "workspace_path": abs_path,
            })
        except PermissionError as e:
            return f"Security error: {e}"
        except Exception as e:
            return f"Error writing to workspace: {e}"


class WorkspaceReadTool(BaseTool):
    """Read a file from the current task's workspace."""

    @property
    def name(self) -> str:
        return "workspace_read"

    @property
    def description(self) -> str:
        return (
            "Read a file from your task workspace. Use this to retrieve "
            "code, data, or results that were previously written."
        )

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Relative path within the workspace to read (e.g. 'output.txt')",
                },
            },
            "required": ["file_path"],
        }

    async def execute(self, file_path: str, **kwargs) -> str:
        task_id = kwargs.get("_task_id")
        if not task_id:
            return "Error: No active task workspace."
        try:
            content = _workspace_mgr.read_file(task_id, file_path)
            # Truncate very large files
            if len(content) > 50000:
                content = content[:50000] + f"\n\n... [Truncated. Full file is {len(content)} chars]"
            return content
        except FileNotFoundError as e:
            return f"File not found: {e}"
        except PermissionError as e:
            return f"Security error: {e}"
        except Exception as e:
            return f"Error reading from workspace: {e}"


class WorkspaceListTool(BaseTool):
    """List all files in the current task's workspace."""

    @property
    def name(self) -> str:
        return "workspace_list"

    @property
    def description(self) -> str:
        return (
            "List all files in your task workspace with their sizes and paths. "
            "Use this to see what files are available."
        )

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {},
        }

    async def execute(self, **kwargs) -> str:
        task_id = kwargs.get("_task_id")
        if not task_id:
            return "Error: No active task workspace."
        files = _workspace_mgr.list_files(task_id)
        if not files:
            return "Workspace is empty. No files have been written yet."

        total_size = sum(f["size"] for f in files)
        lines = [f"Workspace files ({len(files)} files, {total_size:,} bytes total):", ""]
        for f in files:
            lines.append(f"  {f['path']}  ({f['size']:,} bytes, modified {f['modified']})")
        return "\n".join(lines)


class WorkspaceRunShellTool(BaseTool):
    """Execute a shell command within the task workspace directory."""

    @property
    def name(self) -> str:
        return "workspace_shell"

    @property
    def description(self) -> str:
        return (
            "Execute a shell command with the workspace directory as working "
            "directory. Use this to run scripts, compile code, or process files. "
            "Commands run with a 30-second timeout."
        )

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute (e.g. 'python main.py', 'ls -la')",
                },
            },
            "required": ["command"],
        }

    async def execute(self, command: str, **kwargs) -> str:
        task_id = kwargs.get("_task_id")
        if not task_id:
            return "Error: No active task workspace."
        ws_path = _workspace_mgr.get_path(task_id)
        if not ws_path:
            return "Error: Workspace directory does not exist."

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=ws_path,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
            except asyncio.TimeoutError:
                proc.kill()
                return f"Command timed out after 30 seconds: {command}"

            output = stdout.decode("utf-8", errors="replace")
            err = stderr.decode("utf-8", errors="replace")
            result = f"Exit code: {proc.returncode}\n"
            if output:
                result += f"\n[stdout]\n{output}"
            if err:
                result += f"\n[stderr]\n{err}"
            return result or "(no output)"

        except Exception as e:
            return f"Error executing command: {e}"
