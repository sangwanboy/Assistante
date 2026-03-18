from datetime import datetime, timezone
import uuid

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid.uuid4())


class WebWorkspace(Base):
    __tablename__ = "web_workspaces"
    __table_args__ = (
        Index("ix_web_workspaces_owner", "owner_agent_id"),
        Index("ix_web_workspaces_status", "status"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    owner_agent_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    project_type: Mapped[str] = mapped_column(String, default="static")
    status: Mapped[str] = mapped_column(String, default="CREATED")
    entry_url: Mapped[str | None] = mapped_column(String, nullable=True)
    preview_container_id: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
