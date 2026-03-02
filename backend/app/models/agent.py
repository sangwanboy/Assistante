from datetime import datetime, timezone
from typing import Optional
import uuid
from sqlalchemy import String, Text, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

def utcnow():
    return datetime.now(timezone.utc)

def new_id():
    return str(uuid.uuid4())

class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str] = mapped_column(String)  # openai, anthropic, gemini, ollama
    model: Mapped[str] = mapped_column(String)
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # ── Soul (Personality) ──
    personality_tone: Mapped[str | None] = mapped_column(Text, nullable=True)         # e.g. "professional", "friendly", "sarcastic"
    personality_traits: Mapped[str | None] = mapped_column(Text, nullable=True)       # JSON list: ["curious", "concise", "creative"]
    communication_style: Mapped[str | None] = mapped_column(Text, nullable=True)      # "formal", "casual", "technical", "storytelling"

    # ── Mind (Tools & Reasoning) ──
    enabled_tools: Mapped[str | None] = mapped_column(Text, nullable=True)            # JSON list: ["web_search", "code_executor", ...]
    reasoning_style: Mapped[str | None] = mapped_column(Text, nullable=True)          # "analytical", "creative", "balanced", "step-by-step"

    # ── Memory (Persistent Context) ──
    memory_context: Mapped[str | None] = mapped_column(Text, nullable=True)           # persistent context notes
    memory_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)      # standing instructions

    # ── Per-Agent API Key ──
    api_key: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Core system flag (protects from deletion)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
