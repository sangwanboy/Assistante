"""Announcement model for broadcast messages with per-agent acknowledgement tracking."""

from datetime import datetime, timezone
import uuid

from sqlalchemy import String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow():
    return datetime.now(timezone.utc)


def new_id():
    return str(uuid.uuid4())


class Announcement(Base):
    """Tracks broadcast announcements sent to a channel with per-agent acknowledgement."""
    __tablename__ = "announcements"
    __table_args__ = (
        Index("ix_announcements_channel_id", "channel_id"),
        Index("ix_announcements_execution_state", "execution_state"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    channel_id: Mapped[str] = mapped_column(String, ForeignKey("channels.id", ondelete="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="")

    # JSON list of agent IDs this announcement targets
    target_agents: Mapped[str] = mapped_column(Text, default="[]")

    # JSON dict mapping agent_id -> acknowledgement timestamp
    acknowledgements: Mapped[str] = mapped_column(Text, default="{}")

    # Execution state: pending, broadcasting, completed, failed
    execution_state: Mapped[str] = mapped_column(String, default="pending")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
