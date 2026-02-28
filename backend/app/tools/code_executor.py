import subprocess
import sys
import tempfile
import os

from app.tools.base import BaseTool


class CodeExecutorTool(BaseTool):
    @property
    def name(self) -> str:
        return "code_executor"

    @property
    def description(self) -> str:
        return "Execute Python code in a sandboxed subprocess. Use for calculations, data processing, or quick scripts. Returns stdout and stderr."

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute",
                },
            },
            "required": ["code"],
        }

    async def execute(self, code: str, **kwargs) -> str:
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            ) as f:
                f.write(code)
                tmp_path = f.name

            try:
                result = subprocess.run(
                    [sys.executable, tmp_path],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=tempfile.gettempdir(),
                )

                output = ""
                if result.stdout:
                    output += result.stdout
                if result.stderr:
                    output += f"\n[stderr]\n{result.stderr}"
                if result.returncode != 0:
                    output += f"\n[exit code: {result.returncode}]"

                return output.strip() or "(no output)"

            finally:
                os.unlink(tmp_path)

        except subprocess.TimeoutExpired:
            return "Error: Code execution timed out (30s limit)."
        except Exception as e:
            return f"Error: {str(e)}"
