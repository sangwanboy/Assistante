from datetime import datetime
from pydantic import BaseModel, ConfigDict
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

class AgentOut(AgentBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
