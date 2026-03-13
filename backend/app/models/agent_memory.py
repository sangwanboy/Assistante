"""Three-layer agent memory architecture: Working Memory, Episodic Memory,
Semantic Memory, and Conversation Archive."""

from datetime import datetime, timezone
import uuid

from sqlalchemy import String, Text, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow():
    return datetime.now(timezone.utc)


def new_id():
    return str(uuid.uuid4())


class WorkingMemory(Base):
    """Ephemeral recent interaction memory per agent. Entries expire after a configured TTL."""
    __tablename__ = "working_memory"
    __table_args__ = (
        Index("ix_working_memory_agent_id", "agent_id"),
        Index("ix_working_memory_expires_at", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EpisodicMemory(Base):
    """Completed task summaries stored per agent for long-term recall."""
    __tablename__ = "episodic_memory"
    __table_args__ = (
        Index("ix_episodic_memory_agent_id", "agent_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    task_id: Mapped[str | None] = mapped_column(String, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    outcome: Mapped[str | None] = mapped_column(String, nullable=True)  # success, failure, partial
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SemanticMemory(Base):
    """Tier-2 compressed semantic memories extracted from conversation history.

    Older messages are compacted into structured memory objects instead of
    keeping raw text in the LLM context, reducing token usage by ~70 %.

    memory_type: "fact" | "decision" | "summary"
    embedding:   JSON-serialised float list (optional; populated when a
                 vector-search backend is available).
    """
    __tablename__ = "agent_memories"
    __table_args__ = (
        Index("ix_agent_memories_agent_id", "agent_id"),
        Index("ix_agent_memories_memory_type", "memory_type"),
        Index("ix_agent_memories_topic", "topic"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    memory_type: Mapped[str] = mapped_column(String(32), default="fact")  # fact | decision | summary
    topic: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)  # float[] stored as JSON
    source_message_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)  # original message IDs
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ConversationArchive(Base):
    """Tier-3 raw conversation archive.

    Full message history is stored here but never sent to the LLM.
    Used for audit, replay, and future semantic re-extraction.
    """
    __tablename__ = "conversation_archive"
    __table_args__ = (
        Index("ix_conversation_archive_agent_id", "agent_id"),
        Index("ix_conversation_archive_conversation_id", "conversation_id"),
        Index("ix_conversation_archive_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    conversation_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )
    role: Mapped[str] = mapped_column(String(32), default="user")  # system | user | assistant | tool
    content: Mapped[str] = mapped_column(Text, default="")
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # tool_name, token_count, etc.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
