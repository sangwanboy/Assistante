"""Pydantic schemas for external integrations."""
from __future__ import annotations
from typing import Optional, Any
from pydantic import BaseModel


class IntegrationCreate(BaseModel):
    name: str
    platform: str  # telegram | discord | slack | whatsapp
    config: dict[str, Any] = {}
    agent_id: Optional[str] = None
    is_active: bool = True


class IntegrationUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    agent_id: Optional[str] = None
    is_active: Optional[bool] = None


class IntegrationOut(BaseModel):
    id: str
    name: str
    platform: str
    agent_id: Optional[str]
    is_active: bool
    # Note: config is intentionally excluded from responses (contains secrets)

    model_config = {"from_attributes": True}
