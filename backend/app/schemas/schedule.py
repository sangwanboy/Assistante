"""Pydantic schemas for Agent Schedules (Heartbeat tasks)."""
from __future__ import annotations
from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel


class ScheduleCreate(BaseModel):
    agent_id: str
    name: str
    description: str = ""
    interval_minutes: int = 60
    task_config: dict[str, Any] = {}
    is_active: bool = True


class ScheduleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    interval_minutes: Optional[int] = None
    task_config: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


class ScheduleOut(BaseModel):
    id: str
    agent_id: str
    name: str
    description: str
    interval_minutes: int
    is_active: bool
    last_run: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}
