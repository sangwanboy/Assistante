from datetime import datetime, timezone
import uuid

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid.uuid4())


class OrchestrationRun(Base):
    __tablename__ = "orchestration_runs"
    __table_args__ = (
        Index("ix_orch_runs_conversation", "conversation_id"),
        Index("ix_orch_runs_state", "state"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    conversation_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    root_agent_id: Mapped[str | None] = mapped_column(String, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    strategy: Mapped[str] = mapped_column(String, default="multi_step_tools")
    state: Mapped[str] = mapped_column(String, default="RUNNING", index=True)
    user_request: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    autonomy_report_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    token_usage_total: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_total: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    nodes = relationship("OrchestrationTaskNode", back_populates="run", cascade="all, delete-orphan")
    edges = relationship("OrchestrationTaskEdge", back_populates="run", cascade="all, delete-orphan")


class OrchestrationTaskNode(Base):
    __tablename__ = "orchestration_task_nodes"
    __table_args__ = (
        Index("ix_orch_nodes_run", "run_id"),
        Index("ix_orch_nodes_state", "state"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("orchestration_runs.id", ondelete="CASCADE"), index=True)
    node_key: Mapped[str] = mapped_column(String, index=True)

    type: Mapped[str] = mapped_column(String, default="subtask")
    agent_id: Mapped[str | None] = mapped_column(String, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    state: Mapped[str] = mapped_column(String, default="PENDING")

    inputs_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    outputs_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    prompt_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_calls_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_usage: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    run = relationship("OrchestrationRun", back_populates="nodes")


class OrchestrationTaskEdge(Base):
    __tablename__ = "orchestration_task_edges"
    __table_args__ = (
        Index("ix_orch_edges_run", "run_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("orchestration_runs.id", ondelete="CASCADE"), index=True)
    source_node_key: Mapped[str] = mapped_column(String)
    target_node_key: Mapped[str] = mapped_column(String)
    dependency_type: Mapped[str] = mapped_column(String, default="depends_on")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    run = relationship("OrchestrationRun", back_populates="edges")
