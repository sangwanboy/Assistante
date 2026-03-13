import subprocess
import os

from app.tools.base import BaseTool
from typing import Optional

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

    async def execute(self, command: str, cwd: Optional[str] = None, **kwargs) -> str:
        import asyncio

        # Security: Block dangerous commands
        BLOCKED_PATTERNS = [
            "rm -rf /", "rm -rf /*", "del /s /q", "format c:",
            "mkfs.", ":(){:|:&};:", "dd if=/dev/zero",
            "chmod -R 777 /", "chown -R", "> /dev/sda",
        ]
        cmd_lower = command.lower().strip() if isinstance(command, str) else str(command).lower()
        for pattern in BLOCKED_PATTERNS:
            if pattern in cmd_lower:
                return f"BLOCKED: Command contains dangerous pattern '{pattern}'. This operation is not allowed."

        try:
            # Run powershell non-interactive to prevent hanging on prompts
            process = await asyncio.create_subprocess_exec(
                "powershell", "-NonInteractive", "-Command", command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd or os.getcwd(),
            )

            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60.0)
            except asyncio.TimeoutError:
                process.kill()
                await process.communicate() # wait for it to actually die
                return "Error: Command execution timed out (60s limit)."

            output = ""
            if stdout:
                output += stdout.decode('utf-8', errors='replace')
            if stderr:
                output += f"\n[stderr]\n{stderr.decode('utf-8', errors='replace')}"
            if process.returncode != 0:
                output += f"\n[exit code: {process.returncode}]"

            return output.strip() or "(no output)"

        except Exception as e:
            return f"Error: {str(e)}"
