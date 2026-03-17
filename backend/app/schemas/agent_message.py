"""Pydantic schemas for Agent Messaging (P2P + Group Discussions)."""
from __future__ import annotations
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class AgentMessageCreate(BaseModel):
    from_agent_id: str
    content: str
    to_agent_id: Optional[str] = None
    group_id: Optional[str] = None


class AgentMessageOut(BaseModel):
    id: str
    from_agent_id: str
    to_agent_id: Optional[str]
    group_id: Optional[str]
    content: str
    role: Optional[str] = "agent"
    created_at: datetime
    is_read: Optional[bool] = False

    model_config = {"from_attributes": True}


class GroupDiscussionCreate(BaseModel):
    name: str
    description: str = ""
    agent_ids: List[str] = []


class GroupDiscussionOut(BaseModel):
    id: str
    name: str
    description: str
    agent_ids_json: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
