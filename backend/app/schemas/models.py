from pydantic import BaseModel


class ModelInfoOut(BaseModel):
    id: str
    name: str
    provider: str
    supports_streaming: bool = True
    supports_tools: bool = True
    context_window: int = 8192


class ToolInfoOut(BaseModel):
    name: str
    description: str
    parameters: dict
    is_builtin: bool = True

