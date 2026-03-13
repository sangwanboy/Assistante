"""Task model for tracking delegated agent work items."""

from datetime import datetime, timezone
import uuid

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow():
    return datetime.now(timezone.utc)


def new_id():
    return str(uuid.uuid4())


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_assigned_agent_id", "assigned_agent_id"),
        Index("ix_tasks_lifecycle_stage", "lifecycle_stage"),
        Index("ix_tasks_parent_task_id", "parent_task_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    chain_id: Mapped[str | None] = mapped_column(String, ForeignKey("delegation_chains.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id", ondelete="CASCADE"))
    conversation_id: Mapped[str | None] = mapped_column(String, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)

    # Subtask hierarchy (self-referential)
    parent_task_id: Mapped[str | None] = mapped_column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)
    subtasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="parent_task", cascade="all, delete-orphan"
    )
    parent_task: Mapped["Task | None"] = relationship(
        "Task", back_populates="subtasks", remote_side="Task.id"
    )

    # Task Contract
    goal: Mapped[str] = mapped_column(Text, default="")
    expected_output_schema: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status & Results
    status: Mapped[str] = mapped_column(String, default="pending", index=True)
    lifecycle_stage: Mapped[str] = mapped_column(String, default="pending")  # pending, queued, running, review, done, failed
    prompt: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Progress tracking
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    
    @property
    def progress_percent(self) -> int:
        return self.progress
        
    @progress_percent.setter
    def progress_percent(self, value: int):
        self.progress = value
    checkpoint: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timeout & retry
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=900)  # 15 minutes
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)

    # autonomous limits & trackers
    max_steps: Mapped[int] = mapped_column(Integer, default=40)
    max_tool_calls: Mapped[int] = mapped_column(Integer, default=12)
    max_tokens: Mapped[int] = mapped_column(Integer, default=200000)
    step_count: Mapped[int] = mapped_column(Integer, default=0)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
