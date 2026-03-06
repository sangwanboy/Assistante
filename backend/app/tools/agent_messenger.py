"""AgentMessengerTool: allows agents to send P2P and group messages to other agents."""
from __future__ import annotations
import json
import logging

from app.tools.base import BaseTool
from app.services.agent_messaging import AgentMessagingService

logger = logging.getLogger(__name__)


class AgentMessengerTool(BaseTool):
    """Send a direct or group message to one or more other agents asynchronously.

    Use this tool when you need to:
    - Ask another agent a question without waiting for the answer immediately
    - Share information with all agents in a group discussion
    - Delegate a subtask in parallel to multiple agents
    """

    @property
    def name(self) -> str:
        return "agent_messenger"

    @property
    def description(self) -> str:
        return (
            "Send an asynchronous message to another agent (direct) or to all agents "
            "in a group discussion. Messages are delivered to the recipient's inbox "
            "and visible in the Agent Messaging panel. The main system agent is always "
            "included in group discussions."
        )

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["send_direct", "send_group", "list_groups", "create_group", "get_inbox"],
                    "description": "Action to perform",
                },
                "from_agent_id": {
                    "type": "string",
                    "description": "ID of the sending agent (required for send_* actions)",
                },
                "to_agent_id": {
                    "type": "string",
                    "description": "Recipient agent ID (for send_direct)",
                },
                "group_id": {
                    "type": "string",
                    "description": "Group discussion ID (for send_group)",
                },
                "content": {
                    "type": "string",
                    "description": "Message content",
                },
                "group_name": {
                    "type": "string",
                    "description": "Name for a new group (for create_group)",
                },
                "agent_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of agent IDs to include in a group",
                },
            },
            "required": ["action"],
        }

    def __init__(self, session_factory=None):
        self._session_factory = session_factory

    async def execute(
        self,
        action: str,
        from_agent_id: str | None = None,
        to_agent_id: str | None = None,
        group_id: str | None = None,
        content: str | None = None,
        group_name: str | None = None,
        agent_ids: list[str] | None = None,
        **kwargs,
    ) -> str:
        messaging = AgentMessagingService.get_instance()

        if action == "send_direct":
            if not from_agent_id or not to_agent_id or not content:
                return "Error: send_direct requires from_agent_id, to_agent_id, and content."
            if self._session_factory:
                async with self._session_factory() as session:
                    await messaging.send_direct(from_agent_id, to_agent_id, content, session)
            else:
                await messaging.send_direct(from_agent_id, to_agent_id, content)
            return f"Message sent to agent {to_agent_id}."

        elif action == "send_group":
            if not from_agent_id or not group_id or not content:
                return "Error: send_group requires from_agent_id, group_id, and content."
            participants = await self._get_group_participants(group_id)
            if self._session_factory:
                async with self._session_factory() as session:
                    await messaging.send_group(from_agent_id, group_id, content, participants, session)
            else:
                await messaging.send_group(from_agent_id, group_id, content, participants)
            return f"Message broadcast to group {group_id} ({len(participants)} participants)."

        elif action == "list_groups":
            groups = await self._list_groups()
            return json.dumps(groups, indent=2)

        elif action == "create_group":
            if not group_name or not agent_ids:
                return "Error: create_group requires group_name and agent_ids."
            group = await self._create_group(group_name, agent_ids)
            return f"Group '{group_name}' created with ID {group['id']}."

        elif action == "get_inbox":
            if not from_agent_id:
                return "Error: get_inbox requires from_agent_id."
            inbox = messaging.get_inbox(from_agent_id)
            messages = []
            while not inbox.empty():
                messages.append(inbox.get_nowait())
            return json.dumps(messages, indent=2) if messages else "Inbox is empty."

        return f"Unknown action: {action}"

    async def _get_group_participants(self, group_id: str) -> list[str]:
        if not self._session_factory:
            return []
        from sqlalchemy import select
        from app.models.agent_message import AgentGroupDiscussion
        async with self._session_factory() as session:
            result = await session.execute(
                select(AgentGroupDiscussion).where(AgentGroupDiscussion.id == group_id)
            )
            grp = result.scalar_one_or_none()
            if grp:
                return json.loads(grp.agent_ids_json)
        return []

    async def _list_groups(self) -> list[dict]:
        if not self._session_factory:
            return []
        from sqlalchemy import select
        from app.models.agent_message import AgentGroupDiscussion
        async with self._session_factory() as session:
            result = await session.execute(
                select(AgentGroupDiscussion).where(AgentGroupDiscussion.is_active == True)
            )
            return [
                {"id": g.id, "name": g.name, "agent_ids": json.loads(g.agent_ids_json)}
                for g in result.scalars().all()
            ]

    async def _create_group(self, name: str, agent_ids: list[str]) -> dict:
        if not self._session_factory:
            import uuid
            return {"id": str(uuid.uuid4()), "name": name}
        from app.models.agent_message import AgentGroupDiscussion
        async with self._session_factory() as session:
            grp = AgentGroupDiscussion(
                name=name,
                agent_ids_json=json.dumps(agent_ids),
            )
            session.add(grp)
            await session.commit()
            await session.refresh(grp)
            return {"id": grp.id, "name": grp.name}
