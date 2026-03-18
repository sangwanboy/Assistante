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
from app.services.history_summarization_service import HistorySummarizationService
from app.providers.registry import ProviderRegistry
from app.db.engine import async_session

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
    return await service.create(title=req.title, model=req.model, system_prompt=req.system_prompt, is_group=req.is_group, agent_id=req.agent_id, channel_id=req.channel_id)


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
        conversation_id, title=req.title, model=req.model, system_prompt=req.system_prompt, is_group=req.is_group, agent_id=req.agent_id, channel_id=req.channel_id
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

@router.delete("/{conversation_id}/messages/{message_id}")
async def delete_message(
    conversation_id: str, 
    message_id: int, 
    service: ConversationService = Depends(get_conv_service)
):
    deleted = await service.delete_message(conversation_id, message_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"status": "deleted"}


@router.post("/{conversation_id}/summarize")
async def trigger_conversation_summary(
    conversation_id: str,
    service: ConversationService = Depends(get_conv_service),
):
    conv = await service.get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    summary_service = await HistorySummarizationService.get_instance(
        session_factory=async_session,
        providers=ProviderRegistry(),
    )
    job_id = await summary_service.enqueue(
        thread_id=conversation_id,
        trigger="manual",
        agent_id=conv.agent_id,
    )
    return {"status": "queued", "job_id": job_id}


@router.get("/{conversation_id}/archive/search")
async def search_archive(
    conversation_id: str,
    q: str,
    limit: int = 50,
    service: ConversationService = Depends(get_conv_service),
):
    conv = await service.get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    rows = await service.search_archive(conversation_id, q, limit=limit)
    return [
        {
            "id": row.id,
            "message_id": row.message_id,
            "thread_id": row.thread_id,
            "sender": row.sender,
            "role": row.role,
            "content": row.content,
            "archived": row.archived,
            "timestamp": row.timestamp.isoformat() if row.timestamp else None,
        }
        for row in rows
    ]
