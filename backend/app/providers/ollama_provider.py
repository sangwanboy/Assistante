import json
import httpx
from typing import AsyncIterator

from app.providers.base import BaseProvider, ChatMessage, StreamChunk, ModelInfo


class OllamaProvider(BaseProvider):
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")

    @property
    def name(self) -> str:
        return "ollama"

    def is_available(self) -> bool:
        try:
            import httpx
            r = httpx.get(f"{self.base_url}/api/tags", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    def _format_messages(self, messages: list[ChatMessage]) -> list[dict]:
        formatted = []
        for msg in messages:
            if msg.role == "tool":
                formatted.append({
                    "role": "tool",
                    "content": msg.content,
                })
            else:
                formatted.append({"role": msg.role, "content": msg.content})
        return formatted

    async def complete(
        self,
        messages: list[ChatMessage],
        model: str,
        tools: list[dict] | None = None,
        temperature: float = 0.7,
    ) -> ChatMessage:
        payload = {
            "model": model,
            "messages": self._format_messages(messages),
            "stream": False,
            "options": {"temperature": temperature},
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()

        return ChatMessage(
            role="assistant",
            content=data.get("message", {}).get("content", ""),
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        model: str,
        tools: list[dict] | None = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[StreamChunk]:
        payload = {
            "model": model,
            "messages": self._format_messages(messages),
            "stream": True,
            "options": {"temperature": temperature},
        }

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=120,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    msg = data.get("message", {})
                    done = data.get("done", False)

                    yield StreamChunk(
                        delta=msg.get("content", ""),
                        finish_reason="stop" if done else None,
                    )

    async def list_models(self) -> list[ModelInfo]:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/api/tags", timeout=5)
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            return []

        models = []
        for m in data.get("models", []):
            name = m.get("name", "unknown")
            models.append(
                ModelInfo(
                    id=name,
                    name=name,
                    provider="ollama",
                    supports_tools=False,
                    context_window=m.get("details", {}).get("context_length", 4096),
                )
            )
        return models
