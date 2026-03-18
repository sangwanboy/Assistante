"""REST + WebSocket API for Agent Messaging (P2P + Group discussions)."""
import asyncio
import json
import logging
import re
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session, async_session
from app.models.agent_message import AgentGroupDiscussion
from app.models.agent import Agent
from app.models.channel import Channel
from app.models.channel_agent import ChannelAgent
from app.schemas.agent_message import (
    AgentMessageCreate, AgentMessageOut,
    GroupDiscussionCreate, GroupDiscussionOut,
)
from app.services.agent_messaging import AgentMessagingService

router = APIRouter()
logger = logging.getLogger(__name__)

# Pattern: @all: task  (system agent / user only)
_ALL_RE = re.compile(r'(?i)^@all:\s*(.+)', re.DOTALL)

# Pattern: one or more @AgentName: task blocks in a single message.
# Captures from each @Name: up to the next @Name: or end of string.
# Excludes @all (handled separately above).
_MULTI_MENTION_RE = re.compile(
    r'@(?!all\b)([\w][\w ]*):\s*(.*?)(?=\s*@[\w][\w ]*:|\Z)',
    re.DOTALL | re.IGNORECASE,
)


# ── Group Discussion CRUD ─────────────────────────────────────────────────────

@router.get("/groups", response_model=List[GroupDiscussionOut])
async def list_groups(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(AgentGroupDiscussion).order_by(AgentGroupDiscussion.created_at)
    )
    return result.scalars().all()


@router.post("/groups", response_model=GroupDiscussionOut)
async def create_group(
    body: GroupDiscussionCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a group discussion. The main system agent is always included."""
    system_result = await session.execute(
        select(Agent).where(Agent.is_system)
    )
    system_agent = system_result.scalar_one_or_none()
    participant_ids = list(body.agent_ids)
    if system_agent and system_agent.id not in participant_ids:
        participant_ids.append(system_agent.id)

    group_id = str(uuid.uuid4())
    grp = AgentGroupDiscussion(
        id=group_id,
        name=body.name,
        description=body.description,
        agent_ids_json=json.dumps(participant_ids),
    )
    session.add(grp)

    # Mirror group discussions into chat channels so they appear in Chat UI.
    # Use the same UUID for both entities for deterministic linking.
    channel = Channel(
        id=group_id,
        name=body.name,
        description=body.description,
        is_announcement=False,
    )
    session.add(channel)

    for agent_id in participant_ids:
        session.add(ChannelAgent(channel_id=group_id, agent_id=agent_id))

    await session.commit()
    await session.refresh(grp)
    return grp


@router.delete("/groups/{group_id}")
async def delete_group(group_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(AgentGroupDiscussion).where(AgentGroupDiscussion.id == group_id)
    )
    grp = result.scalar_one_or_none()
    if not grp:
        raise HTTPException(status_code=404, detail="Group not found")

    # Keep mirrored chat channel in sync with group lifecycle.
    channel = await session.get(Channel, group_id)
    if channel:
        await session.delete(channel)

    await session.delete(grp)
    await session.commit()
    return {"ok": True}


# ── Message endpoints ─────────────────────────────────────────────────────────

@router.get("/messages", response_model=List[AgentMessageOut])
async def get_messages(
    agent_id: str | None = None,
    group_id: str | None = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
):
    messaging = AgentMessagingService.get_instance()
    msgs = await messaging.get_messages(
        session, agent_id=agent_id, group_id=group_id, limit=limit
    )
    return msgs


@router.post("/messages/direct", response_model=AgentMessageOut, deprecated=True)
async def send_direct_message(
    body: AgentMessageCreate,
    session: AsyncSession = Depends(get_session),
):
    """Send a direct message between agents. DEPRECATED: Use unified channel chat with @mentions instead."""
    if not body.to_agent_id:
        raise HTTPException(status_code=400, detail="to_agent_id is required for direct messages")

    # Permission check: only system agents can send direct messages
    sender_result = await session.execute(
        select(Agent).where(Agent.id == body.from_agent_id)
    )
    sender = sender_result.scalar_one_or_none()
    if not sender or not sender.is_system:
        raise HTTPException(status_code=403, detail="Only system agents can send direct messages. Use channel @mentions instead.")

    messaging = AgentMessagingService.get_instance()
    msg = await messaging.send_direct(
        body.from_agent_id, body.to_agent_id, body.content, session
    )
    return msg


@router.post("/messages/group", response_model=AgentMessageOut)
async def send_group_message(
    body: AgentMessageCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    if not body.group_id:
        raise HTTPException(status_code=400, detail="group_id is required for group messages")

    # Load group + participant list
    result = await session.execute(
        select(AgentGroupDiscussion).where(AgentGroupDiscussion.id == body.group_id)
    )
    grp = result.scalar_one_or_none()
    if not grp:
        raise HTTPException(status_code=404, detail="Group not found")
    participants = json.loads(grp.agent_ids_json)

    messaging = AgentMessagingService.get_instance()
    msg = await messaging.send_group(
        body.from_agent_id, body.group_id, body.content, participants, session
    )

    content = body.content.strip()
    provider_registry = getattr(request.app.state, "provider_registry", None)
    tool_registry = getattr(request.app.state, "tool_registry", None)

    if provider_registry:
        # ── @all: task  (system agent / user only) ──────────────────────────
        all_match = _ALL_RE.match(content)
        if all_match:
            # Verify sender is a system agent
            sender_result = await session.execute(
                select(Agent).where(Agent.id == body.from_agent_id)
            )
            sender = sender_result.scalar_one_or_none()
            if sender and sender.is_system:
                task = all_match.group(1).strip()
                for agent_id in participants:
                    if agent_id == body.from_agent_id:
                        continue  # don't delegate to self
                    asyncio.create_task(_auto_delegate(
                        task=task,
                        group_id=body.group_id,
                        participants=participants,
                        from_agent_id=body.from_agent_id,
                        provider_registry=provider_registry,
                        tool_registry=tool_registry,
                        target_agent_id=agent_id,
                    ))
            else:
                logger.warning(
                    "@all: blocked — sender %s is not a system agent", body.from_agent_id
                )

        else:
            # ── Multiple @AgentName: task mentions ──────────────────────────
            for m in _MULTI_MENTION_RE.finditer(content):
                agent_name = m.group(1).strip()
                task = m.group(2).strip()
                if not task:
                    continue
                asyncio.create_task(_auto_delegate(
                    task=task,
                    group_id=body.group_id,
                    participants=participants,
                    from_agent_id=body.from_agent_id,
                    provider_registry=provider_registry,
                    tool_registry=tool_registry,
                    agent_name=agent_name,
                ))

    return msg


# ── Core delegation coroutine ─────────────────────────────────────────────────

async def _auto_delegate(
    task: str,
    group_id: str,
    participants: list,
    from_agent_id: str,
    provider_registry,
    tool_registry=None,
    agent_name: str | None = None,
    target_agent_id: str | None = None,
) -> None:
    """
    Resolve the target agent (by name or direct ID), run delegate_to_agent,
    and post the result back to the group.

    Either `agent_name` or `target_agent_id` must be provided.
    """
    from app.services.chat_service import ChatService

    async with async_session() as session:
        # ── Resolve target agent ───────────────────────────────────────────
        if target_agent_id:
            target = await session.get(Agent, target_agent_id)
            if not target or not target.is_active:
                logger.warning("_auto_delegate: agent id %r not found or inactive", target_agent_id)
                return
        elif agent_name:
            result = await session.execute(
                select(Agent)
                .where(Agent.name.ilike(f"%{agent_name}%"))
                .where(Agent.is_active)
            )
            target = result.scalars().first()
            if not target:
                logger.warning("_auto_delegate: no active agent matching %r", agent_name)
                return
        else:
            logger.warning("_auto_delegate: called with neither agent_name nor target_agent_id")
            return

        # ── Resolve requester name ─────────────────────────────────────────
        req_result = await session.execute(
            select(Agent).where(Agent.id == from_agent_id)
        )
        requester = req_result.scalar_one_or_none()
        requester_name = requester.name if requester else "User"

        # ── Run the task via the agent's personal LLM chat ────────────────
        chat_service = ChatService(
            provider_registry=provider_registry,
            tool_registry=tool_registry,
            session=session,
        )
        try:
            response_text, _ = await chat_service.delegate_to_agent(
                target.id, task, delegated_by=requester_name
            )
        except Exception as exc:
            logger.exception("_auto_delegate: delegation failed for agent %s", target.name)
            response_text = f"[Error executing task: {exc}]"

    # ── Post result back to the group as the target agent ─────────────────
    reply = f"[📋 Result for @{requester_name}]\n\n{response_text}"
    async with async_session() as session2:
        messaging = AgentMessagingService.get_instance()
        await messaging.send_group(target.id, group_id, reply, participants, session2)


# ── WebSocket for real-time agent message feed ────────────────────────────────

@router.websocket("/ws")
async def agent_messaging_ws(websocket: WebSocket):
    await websocket.accept()
    messaging = AgentMessagingService.get_instance()

    # Send recent messages on connect
    async with async_session() as session:
        recent = await messaging.get_messages(session, limit=20)
    await websocket.send_text(json.dumps({"type": "history", "messages": recent}))

    queue = messaging.subscribe_ws()
    try:
        while True:
            msg = await queue.get()
            await websocket.send_text(msg)
    except WebSocketDisconnect:
        messaging.unsubscribe_ws(queue)
    except Exception:
        messaging.unsubscribe_ws(queue)
