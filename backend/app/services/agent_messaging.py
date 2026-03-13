"""AgentMessagingService: asynchronous P2P and group messaging between agents.

Architecture:
  - Each agent has an asyncio.Queue for incoming messages.
  - WebSocket subscribers (frontend) also get notified of new messages.
  - Group discussions always include the main system agent.
  - Agents can send messages using the AgentMessengerTool.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class AgentMessagingService:
    """Singleton that manages inter-agent message routing."""

    _instance: AgentMessagingService | None = None

    def __init__(self) -> None:
        # Per-agent inbox queues: agent_id -> Queue of dict payloads
        self._inboxes: dict[str, asyncio.Queue] = {}
        # WebSocket subscribers (frontend observers)
        self._ws_subscribers: list[asyncio.Queue] = []

    @classmethod
    def get_instance(cls) -> "AgentMessagingService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Inbox management ──────────────────────────────────────────────────────

    def get_inbox(self, agent_id: str) -> asyncio.Queue:
        """Get (or create) the inbox queue for an agent."""
        if agent_id not in self._inboxes:
            self._inboxes[agent_id] = asyncio.Queue()
        return self._inboxes[agent_id]

    # ── WebSocket subscribers (frontend) ──────────────────────────────────────

    def subscribe_ws(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._ws_subscribers.append(q)
        return q

    def unsubscribe_ws(self, q: asyncio.Queue) -> None:
        self._ws_subscribers.discard(q) if hasattr(self._ws_subscribers, 'discard') else None
        try:
            self._ws_subscribers.remove(q)
        except ValueError:
            pass

    async def _broadcast_ws(self, payload: dict) -> None:
        text = json.dumps(payload)
        for q in list(self._ws_subscribers):
            await q.put(text)

    # ── Message sending ───────────────────────────────────────────────────────

    async def send_direct(
        self,
        from_agent_id: str,
        to_agent_id: str,
        content: str,
        session=None,
    ) -> dict:
        """Send a direct P2P message from one agent to another."""
        msg_id = _new_id()
        ts = datetime.now(timezone.utc).isoformat()
        payload = {
            "id": msg_id,
            "from_agent_id": from_agent_id,
            "to_agent_id": to_agent_id,
            "group_id": None,
            "content": content,
            "created_at": ts,
        }

        # Persist to DB if session provided
        if session is not None:
            await _persist_message(session, payload)

        # Deliver to recipient's inbox
        inbox = self.get_inbox(to_agent_id)
        await inbox.put(payload)

        # Notify WebSocket subscribers
        await self._broadcast_ws({"type": "agent_message", "message": payload})
        logger.debug("Direct message from %s to %s", from_agent_id, to_agent_id)
        return payload

    async def send_group(
        self,
        from_agent_id: str,
        group_id: str,
        content: str,
        participant_ids: list[str],
        session=None,
    ) -> dict:
        """Broadcast a message to all participants in a group discussion."""
        msg_id = _new_id()
        ts = datetime.now(timezone.utc).isoformat()
        payload = {
            "id": msg_id,
            "from_agent_id": from_agent_id,
            "to_agent_id": None,
            "group_id": group_id,
            "content": content,
            "created_at": ts,
        }

        if session is not None:
            await _persist_message(session, payload)

        # Deliver to all participants (except sender) inboxes
        for agent_id in participant_ids:
            if agent_id != from_agent_id:
                inbox = self.get_inbox(agent_id)
                await inbox.put(payload)

        await self._broadcast_ws({"type": "group_message", "message": payload})
        logger.debug("Group message from %s to group %s (%d participants)", from_agent_id, group_id, len(participant_ids))
        return payload

    async def get_messages(
        self,
        session,
        agent_id: str | None = None,
        group_id: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Fetch historical messages from DB."""
        from sqlalchemy import select, or_
        from app.models.agent_message import AgentMessage

        stmt = select(AgentMessage).order_by(AgentMessage.created_at.desc()).limit(limit)
        if group_id:
            stmt = stmt.where(AgentMessage.group_id == group_id)
        elif agent_id:
            stmt = stmt.where(
                or_(
                    AgentMessage.from_agent_id == agent_id,
                    AgentMessage.to_agent_id == agent_id,
                )
            )
        result = await session.execute(stmt)
        msgs = result.scalars().all()
        return [
            {
                "id": m.id,
                "from_agent_id": m.from_agent_id,
                "to_agent_id": m.to_agent_id,
                "group_id": m.group_id,
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "is_read": m.is_read,
            }
            for m in reversed(msgs)
        ]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _new_id() -> str:
    import uuid
    return str(uuid.uuid4())


async def _persist_message(session, payload: dict) -> None:
    from app.models.agent_message import AgentMessage
    msg = AgentMessage(
        id=payload["id"],
        from_agent_id=payload["from_agent_id"],
        to_agent_id=payload.get("to_agent_id"),
        group_id=payload.get("group_id"),
        content=payload["content"],
    )
    session.add(msg)
    await session.commit()
