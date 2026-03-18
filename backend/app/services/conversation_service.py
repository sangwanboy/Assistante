from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation, Message
from app.models.context_memory import MessageArchive


class ConversationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, title: str = "New Conversation", model: str = "gemini/gemini-2.5-flash", system_prompt: str | None = None, is_group: bool = False, agent_id: str | None = None, channel_id: str | None = None
    ) -> Conversation:
        conv = Conversation(title=title, model=model, system_prompt=system_prompt, is_group=is_group, agent_id=agent_id, channel_id=channel_id)
        self.session.add(conv)
        await self.session.commit()
        await self.session.refresh(conv)
        return conv

    async def get(self, conversation_id: str) -> Conversation | None:
        stmt = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self, limit: int = 50, offset: int = 0, agent_id: str | None = None, is_group: bool | None = None) -> list[Conversation]:
        stmt = select(Conversation)
        if agent_id:
            stmt = stmt.where(Conversation.agent_id == agent_id)
        if is_group is not None:
            stmt = stmt.where(Conversation.is_group == is_group)
        
        stmt = (
            stmt.order_by(desc(Conversation.updated_at))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, conversation_id: str, **kwargs) -> Conversation | None:
        conv = await self.get(conversation_id)
        if not conv:
            return None
        for key, value in kwargs.items():
            if value is not None and hasattr(conv, key):
                setattr(conv, key, value)
        await self.session.commit()
        await self.session.refresh(conv)
        return conv

    async def delete(self, conversation_id: str) -> bool:
        conv = await self.get(conversation_id)
        if not conv:
            return False
        await self.session.delete(conv)
        await self.session.commit()
        return True

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        agent_name: str | None = None,
        tool_calls_json: str | None = None,
        tool_call_id: str | None = None,
        mentioned_agents_json: str | None = None,
    ) -> Message | None:
        # Block empty/whitespace-only assistant messages that don't have tool calls
        if role == "assistant" and (not content or not str(content).strip()) and not tool_calls_json:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Blocked empty assistant message for conversation {conversation_id} (Agent: {agent_name})")
            return None

        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            agent_name=agent_name,
            tool_calls_json=tool_calls_json,
            tool_call_id=tool_call_id,
            mentioned_agents_json=mentioned_agents_json,
        )
        self.session.add(msg)
        await self.session.commit()
        await self.session.refresh(msg)

        # Keep all raw messages in durable archive for future retrieval.
        archive_row = MessageArchive(
            message_id=msg.id,
            thread_id=conversation_id,
            sender=agent_name or role,
            role=role,
            content=content,
            archived=False,
        )
        self.session.add(archive_row)
        await self.session.commit()
        return msg

    async def search_archive(self, conversation_id: str, query: str, limit: int = 50) -> list[MessageArchive]:
        stmt = (
            select(MessageArchive)
            .where(
                MessageArchive.thread_id == conversation_id,
                MessageArchive.content.ilike(f"%{query}%"),
            )
            .order_by(desc(MessageArchive.timestamp))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_message(self, conversation_id: str, message_id: int) -> bool:
        stmt = select(Message).where(
            Message.id == message_id,
            Message.conversation_id == conversation_id
        )
        result = await self.session.execute(stmt)
        msg = result.scalar_one_or_none()
        if not msg:
            return False
        
        await self.session.delete(msg)
        await self.session.commit()
        return True

    async def get_messages(self, conversation_id: str) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        result = await self.session.execute(stmt)
        messages = list(result.scalars().all())
        
        # Passive Cleanup: Filter out ghost messages (empty assistant messages with no tool calls)
        # to ensure the UI never sees them, even if they exist in the DB.
        filtered = [
            m for m in messages 
            if not (m.role == "assistant" and (not m.content or not str(m.content).strip()) and not m.tool_calls_json)
        ]
        return filtered
