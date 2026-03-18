from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2] / "data" / "web_workspaces"
BASE_DIR.mkdir(parents=True, exist_ok=True)


class WebWorkspaceManager:
    def get_workspace_path(self, workspace_id: str) -> Path:
        return BASE_DIR / workspace_id

    def ensure_workspace(self, workspace_id: str) -> Path:
        path = self.get_workspace_path(workspace_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _resolve_safe_path(self, workspace_id: str, relative_path: str) -> Path:
        root = self.ensure_workspace(workspace_id).resolve()
        candidate = (root / relative_path).resolve()
        if not str(candidate).startswith(str(root)):
            raise PermissionError("Path traversal is not allowed")
        return candidate

    def write_file(self, workspace_id: str, relative_path: str, content: str) -> str:
        target = self._resolve_safe_path(workspace_id, relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return str(target)

    def read_file(self, workspace_id: str, relative_path: str) -> str:
        target = self._resolve_safe_path(workspace_id, relative_path)
        if not target.exists() or not target.is_file():
            raise FileNotFoundError(relative_path)
        return target.read_text(encoding="utf-8", errors="replace")

    def delete_file(self, workspace_id: str, relative_path: str) -> None:
        target = self._resolve_safe_path(workspace_id, relative_path)
        if target.exists() and target.is_file():
            target.unlink()

    def list_files(self, workspace_id: str) -> list[str]:
        root = self.ensure_workspace(workspace_id)
        result: list[str] = []
        for path in root.rglob("*"):
            if path.is_file():
                result.append(path.relative_to(root).as_posix())
        result.sort()
        return result
