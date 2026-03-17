import os
from pathlib import Path
from app.tools.base import BaseTool

class SystemLogsTool(BaseTool):
    @property
    def name(self) -> str:
        return "system_logs_tool"

    @property
    def description(self) -> str:
        return (
            "Read the latest server logs from 'unified_backend.log'. "
            "Use this to diagnose internal errors, verify tool execution flow, "
            "or check for API processing details. Returns the last N lines."
        )

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "lines": {
                    "type": "integer",
                    "description": "Number of lines to read from the tail of the log file",
                    "default": 50,
                },
            },
        }

    async def execute(self, lines: int = 50, **kwargs) -> str:
        try:
            # Absolute path to the unified log file
            log_path = Path(__file__).resolve().parents[2] / "logs" / "unified_backend.log"
            
            if not log_path.exists():
                return f"Error: Log file not found at {log_path}. Ensure unified logging is enabled."

            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                # Basic tail implementation
                all_lines = f.readlines()
                tail = all_lines[-lines:] if lines > 0 else []
                
                if not tail:
                    return "(Log file is empty)"
                
                content = "".join(tail)
                return f"--- Latest {len(tail)} lines of unified_backend.log ---\n{content}"

        except Exception as e:
            return f"Error reading logs: {str(e)}"
