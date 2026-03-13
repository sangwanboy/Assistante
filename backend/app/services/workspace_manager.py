"""Persistent Task Workspace Manager.

Creates, manages, and cleans up per-task sandboxed directories where agents
can read/write files that persist across multiple tool calls within the same
task or autonomous loop run.
"""

import os
import shutil
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Base directory for all task workspaces
WORKSPACES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "workspaces")
WORKSPACES_DIR = os.path.abspath(WORKSPACES_DIR)


class WorkspaceManager:
    """Creates and manages per-task workspaces on the local filesystem.

    Each task gets a directory at data/workspaces/{task_id}/ where agents
    can read, write, and list files. Workspaces persist across tool calls
    within the same task and can be mounted into Docker containers.
    """

    def __init__(self):
        os.makedirs(WORKSPACES_DIR, exist_ok=True)

    def create(self, task_id: str) -> str:
        """Create a workspace directory for a task. Returns the absolute path."""
        ws_path = os.path.join(WORKSPACES_DIR, task_id)
        os.makedirs(ws_path, exist_ok=True)
        logger.info("Created workspace for task %s at %s", task_id, ws_path)
        return ws_path

    def get_path(self, task_id: str) -> str | None:
        """Get the workspace path for a task, or None if it doesn't exist."""
        ws_path = os.path.join(WORKSPACES_DIR, task_id)
        if os.path.isdir(ws_path):
            return ws_path
        return None

    def ensure(self, task_id: str) -> str:
        """Get or create the workspace directory for a task."""
        ws_path = self.get_path(task_id)
        if ws_path:
            return ws_path
        return self.create(task_id)

    def cleanup(self, task_id: str) -> None:
        """Remove a task's workspace directory and all its contents."""
        ws_path = os.path.join(WORKSPACES_DIR, task_id)
        if os.path.isdir(ws_path):
            shutil.rmtree(ws_path, ignore_errors=True)
            logger.info("Cleaned up workspace for task %s", task_id)

    def list_files(self, task_id: str) -> list[dict]:
        """List all files in a task's workspace with metadata.

        Returns list of dicts with 'path' (relative), 'size', 'modified'.
        """
        ws_path = os.path.join(WORKSPACES_DIR, task_id)
        if not os.path.isdir(ws_path):
            return []

        files = []
        for root, _dirs, filenames in os.walk(ws_path):
            for fname in filenames:
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, ws_path)
                stat = os.stat(full)
                files.append({
                    "path": rel.replace("\\", "/"),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                })
        return files

    def read_file(self, task_id: str, file_path: str) -> str:
        """Read a file from the workspace. file_path is relative to workspace root."""
        ws_path = os.path.join(WORKSPACES_DIR, task_id)
        target = os.path.normpath(os.path.join(ws_path, file_path))

        # Security: prevent path traversal
        if not target.startswith(ws_path):
            raise PermissionError(f"Path traversal detected: {file_path}")

        if not os.path.isfile(target):
            raise FileNotFoundError(f"File not found in workspace: {file_path}")

        with open(target, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def write_file(self, task_id: str, file_path: str, content: str) -> str:
        """Write a file to the workspace. Creates parent dirs as needed.
        
        Returns the absolute path to the written file.
        """
        ws_path = os.path.join(WORKSPACES_DIR, task_id)
        os.makedirs(ws_path, exist_ok=True)
        target = os.path.normpath(os.path.join(ws_path, file_path))

        # Security: prevent path traversal
        if not target.startswith(ws_path):
            raise PermissionError(f"Path traversal detected: {file_path}")

        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info("Wrote %d bytes to %s (task %s)", len(content), file_path, task_id)
        return target

    def workspace_size(self, task_id: str) -> int:
        """Get total size of all files in the workspace in bytes."""
        ws_path = os.path.join(WORKSPACES_DIR, task_id)
        if not os.path.isdir(ws_path):
            return 0
        total = 0
        for root, _dirs, filenames in os.walk(ws_path):
            for fname in filenames:
                total += os.path.getsize(os.path.join(root, fname))
        return total

    def list_workspaces(self) -> list[dict]:
        """List all active workspaces with summary info."""
        if not os.path.isdir(WORKSPACES_DIR):
            return []
        result = []
        for entry in os.scandir(WORKSPACES_DIR):
            if entry.is_dir():
                files = self.list_files(entry.name)
                result.append({
                    "task_id": entry.name,
                    "file_count": len(files),
                    "total_size": self.workspace_size(entry.name),
                })
        return result
