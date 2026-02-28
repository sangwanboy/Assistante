from pydantic import BaseModel
from datetime import datetime


class ConversationCreate(BaseModel):
    title: str = "New Conversation"
    model: str = "gemini/gemini-2.5-flash"
    system_prompt: str | None = None
    is_group: bool = False


class ConversationUpdate(BaseModel):
    title: str | None = None
    model: str | None = None
    system_prompt: str | None = None
    is_group: bool | None = None


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    agent_name: str | None = None
    tool_calls_json: str | None = None
    tool_call_id: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationOut(BaseModel):
    id: str
    title: str
    model: str
    system_prompt: str | None
    is_group: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationDetailOut(ConversationOut):
    messages: list[MessageOut] = []
