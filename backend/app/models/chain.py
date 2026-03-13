"""DelegationChain model for tracking multi-agent orchestration flows."""

from datetime import datetime, timezone
import uuid

from sqlalchemy import String, Text, Integer, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow():
    return datetime.now(timezone.utc)


def new_id():
    return str(uuid.uuid4())


class DelegationChain(Base):
    __tablename__ = "delegation_chains"
    __table_args__ = (
        Index("ix_chains_parent_task_id", "parent_task_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    conversation_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    parent_task_id: Mapped[str | None] = mapped_column(String, nullable=True)

    # State: active | completed | halted | failed
    state: Mapped[str] = mapped_column(String, default="active", index=True)
    depth: Mapped[int] = mapped_column(Integer, default=0)
    max_depth: Mapped[int] = mapped_column(Integer, default=6)

    # Agents involved (JSON list of agent IDs)
    agents_involved_json: Mapped[str] = mapped_column(Text, default="[]")

    # Delegation path (JSON list of task IDs tracing the delegation chain)
    delegation_path: Mapped[str] = mapped_column(Text, default="[]")

    # System Agent's orchestration plan summary
    plan_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Token budget tracking
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    max_token_budget: Mapped[int] = mapped_column(Integer, default=100000)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
