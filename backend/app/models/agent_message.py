"""ORM model for Agent-to-Agent Messages (P2P + Group discussions)."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AgentMessage(Base):
    """A message exchanged between agents (P2P or group broadcast)."""
    __tablename__ = "agent_messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    from_agent_id: Mapped[str] = mapped_column(String, nullable=False)
    # If set, this is a direct message to a specific agent
    to_agent_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # If set, this belongs to a group discussion thread
    group_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Role of the sending agent in this message context
    role: Mapped[str] = mapped_column(String, default="agent")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)


class AgentGroupDiscussion(Base):
    """A named group discussion between multiple agents (always includes system agent)."""
    __tablename__ = "agent_group_discussions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    # JSON list of agent IDs participating in this group
    agent_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
