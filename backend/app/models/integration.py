"""ORM model for external channel integrations (Telegram, Discord, Slack, WhatsApp)."""
import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ExternalIntegration(Base):
    __tablename__ = "external_integrations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)             # Human label
    platform: Mapped[str] = mapped_column(String, nullable=False)         # telegram / discord / slack / whatsapp
    config_json: Mapped[str] = mapped_column(Text, default="{}")          # JSON-encoded platform creds
    agent_id: Mapped[str | None] = mapped_column(String, nullable=True)   # Route messages to this agent
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
