import os
from app.tools.base import BaseTool


SAFE_BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "workspace")


class FileManagerTool(BaseTool):
    @property
    def name(self) -> str:
        return "file_manager"

    @property
    def description(self) -> str:
        return "Read, write, or list files in the workspace directory. Useful for saving notes, creating files, or reading file contents."

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["read", "write", "list"],
                    "description": "The file operation to perform",
                },
                "path": {
                    "type": "string",
                    "description": "Relative path within the workspace (for read/write)",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write (for write action)",
                },
            },
            "required": ["action"],
        }

    def _safe_path(self, path: str) -> str:
        os.makedirs(SAFE_BASE_DIR, exist_ok=True)
        full = os.path.normpath(os.path.join(SAFE_BASE_DIR, path))
        if not full.startswith(os.path.normpath(SAFE_BASE_DIR)):
            raise ValueError("Path traversal not allowed")
        return full

    async def execute(self, action: str, path: str = "", content: str = "", **kwargs) -> str:
        try:
            if action == "list":
                target = self._safe_path(path or ".")
                if not os.path.isdir(target):
                    return f"Directory not found: {path}"
                entries = os.listdir(target)
                if not entries:
                    return "Directory is empty."
                return "\n".join(entries)

            if action == "read":
                if not path:
                    return "Error: 'path' is required for read action."
                full = self._safe_path(path)
                if not os.path.isfile(full):
                    return f"File not found: {path}"
                with open(full, "r", encoding="utf-8") as f:
                    return f.read()

            if action == "write":
                if not path:
                    return "Error: 'path' is required for write action."
                full = self._safe_path(path)
                os.makedirs(os.path.dirname(full), exist_ok=True)
                with open(full, "w", encoding="utf-8") as f:
                    f.write(content)
                return f"Successfully wrote to {path}"

            return f"Unknown action: {action}"
        except Exception as e:
            return f"Error: {str(e)}"
