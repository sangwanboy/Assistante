import json
import subprocess
import sys
import tempfile
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.custom_tool import CustomTool
from app.tools.base import BaseTool


class DynamicTool(BaseTool):
    """A BaseTool wrapper around a user-defined custom tool from the database."""

    def __init__(self, ct: CustomTool):
        self._name = ct.name
        self._description = ct.description
        self._params = json.loads(ct.parameters_schema) if ct.parameters_schema else {}
        self._code = ct.code

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def parameters_schema(self) -> dict:
        return self._params

    async def execute(self, **params) -> str:
        return _run_custom_code(self._code, params)


def _run_custom_code(code: str, params: dict) -> str:
    """Execute user-supplied Python code in a subprocess sandbox.

    The code receives a `params` dict as a global variable.  stdout is
    captured and returned.  Execution is limited to 30 seconds.
    """
    wrapper = (
        "import json, sys\n"
        f"params = json.loads({json.dumps(json.dumps(params))})\n"
        f"{code}\n"
    )
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(wrapper)
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


class CustomToolService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(self) -> list[CustomTool]:
        result = await self.session.execute(
            select(CustomTool).order_by(CustomTool.created_at.desc())
        )
        return list(result.scalars().all())

    async def get(self, tool_id: str) -> CustomTool | None:
        return await self.session.get(CustomTool, tool_id)

    async def create(self, **kwargs) -> CustomTool:
        ct = CustomTool(**kwargs)
        self.session.add(ct)
        await self.session.commit()
        await self.session.refresh(ct)
        return ct

    async def update(self, tool_id: str, **kwargs) -> CustomTool | None:
        ct = await self.get(tool_id)
        if not ct:
            return None
        for k, v in kwargs.items():
            if v is not None:
                setattr(ct, k, v)
        await self.session.commit()
        await self.session.refresh(ct)
        return ct

    async def delete(self, tool_id: str) -> bool:
        ct = await self.get(tool_id)
        if not ct:
            return False
        await self.session.delete(ct)
        await self.session.commit()
        return True

    async def test_execute(self, tool_id: str, arguments: dict) -> tuple[bool, str]:
        ct = await self.get(tool_id)
        if not ct:
            return False, "Tool not found."
        try:
            output = _run_custom_code(ct.code, arguments)
            success = not output.startswith("Error:")
            return success, output
        except Exception as e:
            return False, str(e)

    async def get_active_tools(self) -> list[CustomTool]:
        result = await self.session.execute(
            select(CustomTool).where(CustomTool.is_active == True).order_by(CustomTool.name)
        )
        return list(result.scalars().all())
