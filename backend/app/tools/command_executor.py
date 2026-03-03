import subprocess
import os

from app.tools.base import BaseTool

class CommandExecutorTool(BaseTool):
    @property
    def name(self) -> str:
        return "command_executor"

    @property
    def description(self) -> str:
        return "Execute commands in the PowerShell CLI. Use for system navigation, file operations, or running scripts. Returns stdout and stderr."

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "PowerShell command to execute",
                },
                "cwd": {
                    "type": "string",
                    "description": "Optional directory to run the command in. Defaults to the current working directory.",
                }
            },
            "required": ["command"],
        }

    async def execute(self, command: str, cwd: str = None, **kwargs) -> str:
        try:
            # Use powershell as the shell
            result = subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=cwd or os.getcwd(),
            )

            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"
            if result.returncode != 0:
                output += f"\n[exit code: {result.returncode}]"

            return output.strip() or "(no output)"

        except subprocess.TimeoutExpired:
            return "Error: Command execution timed out (60s limit)."
        except Exception as e:
            return f"Error: {str(e)}"
