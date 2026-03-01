from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional

class AgentBase(BaseModel):
    name: str
    description: Optional[str] = None
    provider: str
    model: str
    system_prompt: Optional[str] = None
    is_active: bool = True
    # Soul
    personality_tone: Optional[str] = None
    personality_traits: Optional[str] = None        # JSON list
    communication_style: Optional[str] = None
    # Mind
    enabled_tools: Optional[str] = None             # JSON list
    reasoning_style: Optional[str] = None
    # Memory
    memory_context: Optional[str] = None
    memory_instructions: Optional[str] = None
    # Per-agent API key
    api_key: Optional[str] = None

class AgentCreate(AgentBase):
    pass

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    is_active: Optional[bool] = None
    # Soul
    personality_tone: Optional[str] = None
    personality_traits: Optional[str] = None
    communication_style: Optional[str] = None
    # Mind
    enabled_tools: Optional[str] = None
    reasoning_style: Optional[str] = None
    # Memory
    memory_context: Optional[str] = None
    memory_instructions: Optional[str] = None
    api_key: Optional[str] = None

class AgentOut(AgentBase):
    id: str
    is_system: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator('api_key', mode='before')
    @classmethod
    def mask_api_key(cls, v: str | None) -> str | None:
        if not v:
            return None
        return '•' * (len(v) - 4) + v[-4:] if len(v) > 4 else '•' * len(v)
