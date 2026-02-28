from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationOut,
    ConversationDetailOut,
)
from app.services.conversation_service import ConversationService

router = APIRouter()


def get_conv_service(session: AsyncSession = Depends(get_session)) -> ConversationService:
    return ConversationService(session)


@router.get("", response_model=list[ConversationOut])
async def list_conversations(
    limit: int = 50, offset: int = 0, agent_id: str | None = None, service: ConversationService = Depends(get_conv_service)
):
    return await service.list_all(limit=limit, offset=offset, agent_id=agent_id)


@router.post("", response_model=ConversationOut)
async def create_conversation(
    req: ConversationCreate, service: ConversationService = Depends(get_conv_service)
):
    return await service.create(title=req.title, model=req.model, system_prompt=req.system_prompt, is_group=req.is_group, agent_id=req.agent_id)


@router.get("/{conversation_id}", response_model=ConversationDetailOut)
async def get_conversation(
    conversation_id: str, service: ConversationService = Depends(get_conv_service)
):
    conv = await service.get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.patch("/{conversation_id}", response_model=ConversationOut)
async def update_conversation(
    conversation_id: str, req: ConversationUpdate, service: ConversationService = Depends(get_conv_service)
):
    conv = await service.update(
        conversation_id, title=req.title, model=req.model, system_prompt=req.system_prompt, is_group=req.is_group, agent_id=req.agent_id
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str, service: ConversationService = Depends(get_conv_service)
):
    deleted = await service.delete(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "deleted"}
