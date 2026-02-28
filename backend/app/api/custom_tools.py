from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.schemas.custom_tool import (
    CustomToolCreate,
    CustomToolUpdate,
    CustomToolOut,
    CustomToolTestRequest,
    CustomToolTestResponse,
)
from app.services.custom_tool_service import CustomToolService, DynamicTool

router = APIRouter()


@router.get("", response_model=list[CustomToolOut])
async def list_custom_tools(session: AsyncSession = Depends(get_session)):
    svc = CustomToolService(session)
    return await svc.list_all()


@router.post("", response_model=CustomToolOut, status_code=201)
async def create_custom_tool(
    data: CustomToolCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    svc = CustomToolService(session)
    ct = await svc.create(**data.model_dump())
    # Register into live registry so agents can use it immediately
    if ct.is_active:
        registry = request.app.state.tool_registry
        registry.register(DynamicTool(ct))
    return ct


@router.get("/{tool_id}", response_model=CustomToolOut)
async def get_custom_tool(tool_id: str, session: AsyncSession = Depends(get_session)):
    svc = CustomToolService(session)
    ct = await svc.get(tool_id)
    if not ct:
        raise HTTPException(404, "Custom tool not found")
    return ct


@router.put("/{tool_id}", response_model=CustomToolOut)
async def update_custom_tool(
    tool_id: str,
    data: CustomToolUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    svc = CustomToolService(session)
    ct = await svc.update(tool_id, **data.model_dump(exclude_unset=True))
    if not ct:
        raise HTTPException(404, "Custom tool not found")
    # Re-register into live registry
    registry = request.app.state.tool_registry
    if ct.is_active:
        registry.register(DynamicTool(ct))
    else:
        registry.unregister(ct.name)
    return ct


@router.delete("/{tool_id}")
async def delete_custom_tool(
    tool_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    svc = CustomToolService(session)
    ct = await svc.get(tool_id)
    if ct:
        request.app.state.tool_registry.unregister(ct.name)
    deleted = await svc.delete(tool_id)
    if not deleted:
        raise HTTPException(404, "Custom tool not found")
    return {"status": "deleted"}


@router.post("/{tool_id}/test", response_model=CustomToolTestResponse)
async def test_custom_tool(
    tool_id: str,
    data: CustomToolTestRequest,
    session: AsyncSession = Depends(get_session),
):
    svc = CustomToolService(session)
    success, output = await svc.test_execute(tool_id, data.arguments)
    return CustomToolTestResponse(success=success, output=output)
