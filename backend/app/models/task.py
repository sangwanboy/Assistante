"""Task model for tracking delegated agent work items."""

from datetime import datetime, timezone
import uuid

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow():
    return datetime.now(timezone.utc)


def new_id():
    return str(uuid.uuid4())


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    chain_id: Mapped[str | None] = mapped_column(String, ForeignKey("delegation_chains.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id", ondelete="CASCADE"))
    conversation_id: Mapped[str | None] = mapped_column(String, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)

    # Status: pending | running | completed | failed | cancelled
    status: Mapped[str] = mapped_column(String, default="pending", index=True)
    prompt: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Progress tracking
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    checkpoint: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timeout & retry
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=60)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
