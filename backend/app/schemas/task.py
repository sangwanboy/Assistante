"""Pydantic schemas for Task and DelegationChain API responses."""

from datetime import datetime
from pydantic import BaseModel


class TaskOut(BaseModel):
    id: str
    chain_id: str | None = None
    assigned_agent_id: str
    conversation_id: str | None = None
    parent_task_id: str | None = None
    goal: str = ""
    expected_output_schema: str | None = None
    status: str
    lifecycle_stage: str = "pending"
    prompt: str
    result: str | None = None
    progress: int = 0
    checkpoint: str | None = None
    timeout_seconds: int = 900
    retry_count: int = 0
    max_retries: int = 3
    max_steps: int = 40
    max_tool_calls: int = 12
    max_tokens: int = 200000
    step_count: int = 0
    tokens_used: int = 0
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
    max_depth: int = 6
    agents_involved_json: str = "[]"
    delegation_path: str = "[]"
    plan_summary: str | None = None
    total_tokens_used: int = 0
    max_token_budget: int = 100000
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
