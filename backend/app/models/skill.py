from datetime import datetime, timezone
import uuid
from sqlalchemy import String, Text, Boolean, DateTime, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow():
    return datetime.now(timezone.utc)


def new_id():
    return str(uuid.uuid4())


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    instructions: Mapped[str] = mapped_column(Text)                     # Markdown body (the skill's instructions)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    user_invocable: Mapped[bool] = mapped_column(Boolean, default=True)
    trigger_pattern: Mapped[str | None] = mapped_column(Text, nullable=True)  # Glob pattern e.g. "**/*.tsx"
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)    # Extra OpenClaw fields as JSON

    # -- Skill Governance --
    lifecycle_stage: Mapped[str] = mapped_column(String, default="deployed")  # proposed, review, deployed, deprecated
    security_flags: Mapped[str | None] = mapped_column(Text, nullable=True)   # JSON flags for security concerns
    sandbox_result: Mapped[str | None] = mapped_column(Text, nullable=True)   # Result of sandbox validation
    proposed_by_agent_id: Mapped[str | None] = mapped_column(String, nullable=True)  # Agent that proposed this skill

    # -- Skill Metrics --
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    total_execution_cost: Mapped[float] = mapped_column(Float, default=0.0)
    usage_frequency: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
