from datetime import datetime, timezone
from typing import Optional
import uuid
from sqlalchemy import String, Text, Boolean, DateTime, Float, Integer, Index, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
import enum


class AgentStatus(str, enum.Enum):
    """Persistent lifecycle state for an agent.

    active  — fully operational, can receive tasks
    idle    — running but waiting; reserved capacity
    paused  — temporarily suspended; reserved capacity
    deleted — soft-deleted; capacity will be freed
    """
    active  = "active"
    idle    = "idle"
    paused  = "paused"
    deleted = "deleted"

from app.db.base import Base

def utcnow():
    return datetime.now(timezone.utc)

def new_id():
    return str(uuid.uuid4())

class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = (
        Index("ix_agents_is_active", "is_active"),
        Index("ix_agents_is_system", "is_system"),
        Index("ix_agents_role", "role"),
        Index("ix_agents_provider", "provider"),
        Index("ix_agents_status", "status"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str] = mapped_column(String)  # openai, anthropic, gemini, ollama
    model: Mapped[str] = mapped_column(String)
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Lifecycle state: active | idle | paused | deleted  (soft-delete support)
    # Only 'deleted' status frees agent capacity — all other states reserve a slot.
    status: Mapped[str] = mapped_column(
        String(20), default="active", server_default="active", nullable=False
    )

    # -- Identity --
    role: Mapped[str | None] = mapped_column(String, nullable=True)                    # e.g. "Data Analysis Specialist"
    groups: Mapped[str | None] = mapped_column(Text, nullable=True)                    # JSON list: ["data-team", "engineering-team"]

    # -- Soul (Personality) --
    personality_tone: Mapped[str | None] = mapped_column(Text, nullable=True)         # e.g. "professional", "friendly", "sarcastic"
    personality_traits: Mapped[str | None] = mapped_column(Text, nullable=True)       # JSON list: ["curious", "concise", "creative"]
    communication_style: Mapped[str | None] = mapped_column(Text, nullable=True)      # "formal", "casual", "technical", "storytelling"

    # -- Mind (Tools & Reasoning) --
    enabled_tools: Mapped[str | None] = mapped_column(Text, nullable=True)            # JSON list: ["web_search", "code_executor", ...]
    enabled_skills: Mapped[str | None] = mapped_column(Text, nullable=True)           # JSON list of SKILL.md names
    reasoning_style: Mapped[str | None] = mapped_column(Text, nullable=True)          # "analytical", "creative", "balanced", "step-by-step"

    # -- Memory (Persistent Context) --
    memory_context: Mapped[str | None] = mapped_column(Text, nullable=True)           # persistent context notes
    memory_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)      # standing instructions
    context_window_tokens: Mapped[int] = mapped_column(Integer, default=256000)        # per-agent prune/context window (60k..256k)

    # -- Capabilities & Performance --
    capabilities: Mapped[str | None] = mapped_column(Text, nullable=True)             # JSON list of agent capabilities
    performance_metrics: Mapped[str | None] = mapped_column(Text, nullable=True)      # JSON performance stats

    # -- Per-Agent API Key --
    api_key: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Core system flag (protects from deletion)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)

    # -- Token Economy --
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)

    # -- Heartbeat & Reliability --
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
