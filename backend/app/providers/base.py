from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator

from app.config import settings


@dataclass
class ModelInfo:
    id: str            # e.g. "gpt-4o"
    name: str          # Display name e.g. "GPT-4o"
    provider: str      # "openai", "anthropic", "ollama"
    supports_streaming: bool = True
    supports_tools: bool = True
    context_window: int = 8192
    tpm: int | None = None
    rpm: int | None = None
    rpd: int | None = None


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class ChatMessage:
    role: str          # "system", "user", "assistant", "tool"
    content: str = ""
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None
    images: list[str] | None = None  # List of base64-encoded image strings
    usage: TokenUsage | None = None


@dataclass
class StreamChunk:
    delta: str = ""
    finish_reason: str | None = None
    tool_calls: list[dict] | None = None
    usage: TokenUsage | None = None
    error: str | None = None


class BaseProvider(ABC):
    """Abstract base class that every AI provider must implement."""

    @classmethod
    def get_api_key(cls, provider_name: str) -> str | None:
        """Retrieve provider API key directly from runtime settings."""
        provider = (provider_name or "").strip().lower()
        if provider == "openai":
            return settings.openai_api_key
        if provider == "anthropic":
            return settings.anthropic_api_key
        if provider in {"gemini", "google"}:
            return settings.gemini_api_key
        return None

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
        **kwargs,
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
        **kwargs,
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
