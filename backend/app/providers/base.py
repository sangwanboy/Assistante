from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator


@dataclass
class ModelInfo:
    id: str            # e.g. "gpt-4o"
    name: str          # Display name e.g. "GPT-4o"
    provider: str      # "openai", "anthropic", "ollama"
    supports_streaming: bool = True
    supports_tools: bool = True
    context_window: int = 8192


@dataclass
class ChatMessage:
    role: str          # "system", "user", "assistant", "tool"
    content: str = ""
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None


@dataclass
class StreamChunk:
    delta: str = ""
    finish_reason: str | None = None
    tool_calls: list[dict] | None = None


class BaseProvider(ABC):
    """Abstract base class that every AI provider must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier e.g. 'openai', 'anthropic', 'ollama'."""
        ...

    @abstractmethod
    async def complete(
        self,
        messages: list[ChatMessage],
        model: str,
        tools: list[dict] | None = None,
        temperature: float = 0.7,
    ) -> ChatMessage:
        """Non-streaming completion. Returns a single assistant message."""
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[ChatMessage],
        model: str,
        tools: list[dict] | None = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[StreamChunk]:
        """Streaming completion. Yields text chunks as they arrive."""
        ...

    @abstractmethod
    async def list_models(self) -> list[ModelInfo]:
        """Return models available from this provider."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is configured and usable."""
        ...
