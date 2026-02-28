from datetime import datetime, timezone
import uuid
from sqlalchemy import String, Text, Boolean, DateTime
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
