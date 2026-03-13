from pydantic import BaseModel


class ModelInfoOut(BaseModel):
    id: str
    name: str
    provider: str
    supports_streaming: bool = True
    supports_tools: bool = True
    context_window: int | None = 8192
    rpm: int | None = 100
    tpm: int | None = 1000000
    rpd: int | None = 10000
    is_fallback: bool = False

class ModelCapabilityUpdate(BaseModel):
    rpm: int | None = None
    tpm: int | None = None
    rpd: int | None = None
    context_window: int | None = None

class ToolInfoOut(BaseModel):
    name: str
    description: str
    parameters: dict
    is_builtin: bool = True

