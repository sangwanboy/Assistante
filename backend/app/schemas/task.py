"""Pydantic schemas for Task and DelegationChain API responses."""

from datetime import datetime
from pydantic import BaseModel


class TaskOut(BaseModel):
    id: str
    chain_id: str | None = None
    assigned_agent_id: str
    conversation_id: str | None = None
    status: str
    prompt: str
    result: str | None = None
    progress: int = 0
    checkpoint: str | None = None
    timeout_seconds: int = 60
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    class Config:
        from_attributes = True


class ChainOut(BaseModel):
    id: str
    conversation_id: str | None = None
    parent_task_id: str | None = None
    state: str
    depth: int = 0
    max_depth: int = 5
    agents_involved_json: str = "[]"
    plan_summary: str | None = None
    total_tokens_used: int = 0
    max_token_budget: int = 100000
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
