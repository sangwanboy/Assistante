from pydantic import BaseModel, field_validator
from datetime import datetime


class ConversationCreate(BaseModel):
    title: str = "New Conversation"
    model: str = "gemini/gemini-3.1-flash-lite-preview"
    system_prompt: str | None = None
    is_group: bool = False
    agent_id: str | None = None
    channel_id: str | None = None


class ConversationUpdate(BaseModel):
    title: str | None = None
    model: str | None = None
    system_prompt: str | None = None
    is_group: bool | None = None
    agent_id: str | None = None
    channel_id: str | None = None


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    agent_name: str | None = None
    tool_calls_json: str | None = None
    tool_call_id: str | None = None
    mentioned_agents_json: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationOut(BaseModel):
    id: str
    title: str
    model: str
    system_prompt: str | None
    is_group: bool
    agent_id: str | None
    channel_id: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationDetailOut(ConversationOut):
    messages: list[MessageOut] = []

    @field_validator("messages", mode="after")
    @classmethod
    def filter_ghost_messages(cls, v: list[MessageOut]) -> list[MessageOut]:
        """Filter out assistant messages with no content and no tool calls."""
        return [
            m for m in v
            if not (m.role == "assistant" and (not m.content or not str(m.content).strip()) and not m.tool_calls_json)
        ]
