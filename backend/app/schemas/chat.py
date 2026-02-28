from pydantic import BaseModel


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str
    model: str = "gemini/gemini-2.5-flash"
    temperature: float = 0.7
    system_prompt: str | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    message: str
    role: str = "assistant"


class StreamChunkResponse(BaseModel):
    type: str  # "chunk", "tool_call", "tool_result", "done", "error"
    delta: str = ""
    tool_name: str | None = None
    tool_args: dict | None = None
    tool_result: str | None = None
    message_id: int | None = None
    conversation_id: str | None = None
    error: str | None = None
