from datetime import datetime
from pydantic import BaseModel, Field

class ChannelBase(BaseModel):
    name: str = Field(..., min_length=1)
    description: str | None = None
    is_announcement: bool = False
    orchestration_mode: str = "autonomous"  # "autonomous" | "manual"

class ChannelCreate(ChannelBase):
    pass

class ChannelUpdate(BaseModel):
    name: str | None = Field(None, min_length=1)
    description: str | None = None
    orchestration_mode: str | None = None

class ChannelOut(ChannelBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ChannelAgentAdd(BaseModel):
    agent_id: str
