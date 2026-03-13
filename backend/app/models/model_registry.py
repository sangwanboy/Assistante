from sqlalchemy import String, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class ModelCapability(Base):
    """Registry of known LLM models with their rate limits, capabilities, and routing info."""
    __tablename__ = "model_registry"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    provider: Mapped[str] = mapped_column(String, nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String, nullable=False)

    # Rate Limits
    rpm: Mapped[int | None] = mapped_column(Integer, nullable=True, default=100)
    tpm: Mapped[int | None] = mapped_column(Integer, nullable=True, default=1000000)
    rpd: Mapped[int | None] = mapped_column(Integer, nullable=True, default=10000)

    # Budget & Context
    context_window: Mapped[int | None] = mapped_column(Integer, nullable=True, default=128000)

    # Concurrency
    max_concurrent_requests: Mapped[int] = mapped_column(Integer, default=10)

    # Routing
    is_fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Custom limit overrides
    allow_custom_limits: Mapped[bool] = mapped_column(Boolean, default=True)
