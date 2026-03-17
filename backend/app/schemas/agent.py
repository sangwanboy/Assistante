from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional


MIN_AGENT_GEMINI_MODEL = "gemini-2.5-flash"


def _extract_model_id(model: str) -> str:
    return model.split("/", 1)[1] if "/" in model else model


def _is_disallowed_agent_model(model: str) -> bool:
    model_id = _extract_model_id(model).lower()
    return model_id.startswith("gemini-1.5") or model_id.startswith("gemini-2.0")


def _validate_agent_model_floor(model: str | None) -> str | None:
    if model is None:
        return None
    if _is_disallowed_agent_model(model):
        raise ValueError(
            f"Agent model must be {MIN_AGENT_GEMINI_MODEL} or stronger. Gemini 1.5 and 2.0 models are not allowed for agents."
        )
    return model


class AgentBase(BaseModel):
    name: str
    description: Optional[str] = None
    provider: str
    model: str
    system_prompt: Optional[str] = None
    is_active: bool = True
    # Lifecycle state (active | idle | paused | deleted)
    status: str = "active"
    # Identity
    role: Optional[str] = None
    groups: Optional[str] = None                 # JSON list
    # Soul
    personality_tone: Optional[str] = None
    personality_traits: Optional[str] = None        # JSON list
    communication_style: Optional[str] = None
    # Mind
    enabled_tools: Optional[str] = None             # JSON list
    enabled_skills: Optional[str] = None            # JSON list
    reasoning_style: Optional[str] = None
    # Memory
    memory_context: Optional[str] = None
    memory_instructions: Optional[str] = None
    context_window_tokens: Optional[int] = Field(default=256000, ge=60000, le=256000)
    # Capability Registry (Section 3)
    capabilities: Optional[str] = None              # JSON list: ["orchestration", "coding", "research"]
    performance_metrics: Optional[str] = None       # JSON: {success_rate, tasks_completed, ...}
    # Per-agent API key
    api_key: Optional[str] = None


class AgentCreate(AgentBase):
    @field_validator("model")
    @classmethod
    def validate_model_floor(cls, v: str) -> str:
        return _validate_agent_model_floor(v) or v


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    is_active: Optional[bool] = None
    status: Optional[str] = None  # active | idle | paused | deleted
    # Identity
    role: Optional[str] = None
    groups: Optional[str] = None
    # Soul
    personality_tone: Optional[str] = None
    personality_traits: Optional[str] = None
    communication_style: Optional[str] = None
    # Mind
    enabled_tools: Optional[str] = None
    enabled_skills: Optional[str] = None
    reasoning_style: Optional[str] = None
    # Memory
    memory_context: Optional[str] = None
    memory_instructions: Optional[str] = None
    context_window_tokens: Optional[int] = Field(default=None, ge=60000, le=256000)
    # Capability Registry (Section 3)
    capabilities: Optional[str] = None
    performance_metrics: Optional[str] = None
    api_key: Optional[str] = None

    @field_validator("model")
    @classmethod
    def validate_model_floor(cls, v: Optional[str]) -> Optional[str]:
        return _validate_agent_model_floor(v)


class AgentOut(AgentBase):
    id: str
    is_system: bool
    total_cost: float
    failure_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator('api_key', mode='before')
    @classmethod
    def mask_api_key(cls, v: str | None) -> str | None:
        if not v:
            return None
        return '•' * (len(v) - 4) + v[-4:] if len(v) > 4 else '•' * len(v)
