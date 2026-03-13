"""Tool Memory Store — TOOL_RESULT_ID extraction and external storage.

Problem: tool results (code execution output, web search results, API responses)
are often 5–50 KB of text that bloat the LLM context window on every turn.

Solution: replace large inline results with a compact TOOL_RESULT_ID reference,
store the full content externally, and dereference only when the LLM requests it.

Reference format injected into message content:
    TOOL_RESULT_ID:{uuid} (tool={name}, size={size_bytes}B)

Storage options (selected via `backend`):
    "memory"   in-process dict — fast, not persistent across restarts (default)
    "redis"    Redis SETEX with configurable TTL (requires redis_client)

Activation:
    This service is opt-in.  To activate, pass a `ToolMemoryStore` instance
    to `ChatService` and call `maybe_compress(messages)` before the LLM call.

Not yet wired into the default chat_service.py flow — activate when ready.
"""

import json
import logging
import uuid
from typing import Literal

logger = logging.getLogger(__name__)

# Messages larger than this threshold are offloaded
DEFAULT_INLINE_THRESHOLD_BYTES = 10_240  # 10 KB

# Redis TTL for stored results (seconds)
REDIS_TTL = 3_600  # 1 hour

StorageBackend = Literal["memory", "redis"]


class ToolMemoryStore:
    """Extracts and externalises large tool results.

    Usage::

        store = ToolMemoryStore(backend="redis", redis_client=rc)
        messages = store.maybe_compress(messages)
        # ... LLM call ...
        # On demand: full_result = store.get(result_id)
    """

    def __init__(
        self,
        backend: StorageBackend = "memory",
        redis_client=None,
        inline_threshold: int = DEFAULT_INLINE_THRESHOLD_BYTES,
    ):
        self.backend = backend
        self._redis = redis_client.redis if redis_client and getattr(redis_client, "available", False) else None
        self.inline_threshold = inline_threshold
        self._memory: dict[str, str] = {}  # in-process store

    # ─────────────────────────────────────────────────────────
    # Compression
    # ─────────────────────────────────────────────────────────

    def maybe_compress(self, messages: list) -> list:
        """Replace large tool messages with TOOL_RESULT_ID references.

        This is a synchronous pass, but store() calls are fire-and-forget.
        Large async stores should be handled with `asyncio.create_task`.
        """
        from app.providers.base import ChatMessage

        compressed: list[ChatMessage] = []
        for msg in messages:
            if msg.role == "tool" and msg.content:
                size = len(msg.content.encode("utf-8", errors="replace"))
                if size > self.inline_threshold:
                    result_id = self._store_sync(msg.content, tool_name=msg.tool_call_id)
                    ref = (
                        f"TOOL_RESULT_ID:{result_id} "
                        f"(tool={msg.tool_call_id or '?'}, size={size}B)"
                    )
                    msg = ChatMessage(
                        role=msg.role,
                        content=ref,
                        tool_call_id=msg.tool_call_id,
                    )
            compressed.append(msg)
        return compressed

    # ─────────────────────────────────────────────────────────
    # Storage
    # ─────────────────────────────────────────────────────────

    def _store_sync(self, content: str, tool_name: str | None = None) -> str:
        """Store content and return its TOOL_RESULT_ID. In-memory only."""
        result_id = str(uuid.uuid4())
        self._memory[result_id] = content
        logger.debug("ToolMemoryStore stored %s (%d bytes)", result_id, len(content))
        return result_id

    async def store(self, content: str, tool_name: str | None = None) -> str:
        """Async store — uses Redis if available, falls back to in-memory."""
        result_id = str(uuid.uuid4())
        if self.backend == "redis" and self._redis is not None:
            try:
                key = f"tool_result:{result_id}"
                await self._redis.setex(key, REDIS_TTL, content)
                return result_id
            except Exception as exc:
                logger.debug("ToolMemoryStore Redis store failed, using memory: %s", exc)
        self._memory[result_id] = content
        return result_id

    # ─────────────────────────────────────────────────────────
    # Retrieval
    # ─────────────────────────────────────────────────────────

    async def get(self, result_id: str) -> str | None:
        """Retrieve a stored tool result by its ID."""
        if result_id in self._memory:
            return self._memory[result_id]
        if self.backend == "redis" and self._redis is not None:
            try:
                data = await self._redis.get(f"tool_result:{result_id}")
                if data:
                    return data
            except Exception:
                pass
        return None

    def get_sync(self, result_id: str) -> str | None:
        return self._memory.get(result_id)

    # ─────────────────────────────────────────────────────────
    # Reference parsing
    # ─────────────────────────────────────────────────────────

    @staticmethod
    def parse_reference(content: str) -> str | None:
        """Extract a TOOL_RESULT_ID from a reference string, or None."""
        if not content or "TOOL_RESULT_ID:" not in content:
            return None
        try:
            # "TOOL_RESULT_ID:{uuid} (...)"
            start = content.index("TOOL_RESULT_ID:") + len("TOOL_RESULT_ID:")
            end = content.index(" ", start) if " " in content[start:] else len(content)
            return content[start:end].strip()
        except ValueError:
            return None

    async def expand_references(self, messages: list) -> list:
        """Replace TOOL_RESULT_ID references with their full content (for retrieval flows)."""
        from app.providers.base import ChatMessage

        expanded = []
        for msg in messages:
            if msg.role == "tool" and msg.content:
                ref_id = self.parse_reference(msg.content)
                if ref_id:
                    full = await self.get(ref_id)
                    if full:
                        msg = ChatMessage(
                            role=msg.role,
                            content=full,
                            tool_call_id=msg.tool_call_id,
                        )
            expanded.append(msg)
        return expanded
