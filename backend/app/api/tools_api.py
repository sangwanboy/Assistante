from fastapi import APIRouter, Request

from app.schemas.models import ToolInfoOut

router = APIRouter()


@router.get("", response_model=list[ToolInfoOut])
async def list_tools(request: Request):
    registry = request.app.state.tool_registry
    return [
        ToolInfoOut(
            name=t["name"],
            description=t["description"],
            parameters=t["parameters"],
            is_builtin=t.get("is_builtin", True),
        )
        for t in registry.list_tools()
    ]

