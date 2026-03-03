"""ORM model for Agent Scheduled Tasks (Heartbeat)."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, Text, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AgentSchedule(Base):
    __tablename__ = "agent_schedules"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    interval_minutes: Mapped[int] = mapped_column(Integer, default=60)   # How often to fire
    task_config_json: Mapped[str] = mapped_column(Text, default="{}")    # JSON with "prompt" etc.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
