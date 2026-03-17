"""Semantic Memory Compaction Service.

Implements Tier-1 → Tier-2 memory compaction:
  - Takes a chunk of older conversation messages
  - Uses a fast LLM to extract key facts / decisions / summaries
  - Stores the result as SemanticMemory rows in the database
  - Optionally archives the raw messages into ConversationArchive (Tier 3)

Target token reduction: ~70 % compared to keeping full history in context.

Tier layout:
  Tier 1  Active context  — system prompt + last 5 messages (in-LLM)
  Tier 2  Semantic store  — SemanticMemory rows in PostgreSQL
  Tier 3  Archive         — ConversationArchive rows in PostgreSQL (never sent to LLM)
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_memory import SemanticMemory, ConversationArchive
from app.providers.base import ChatMessage

logger = logging.getLogger(__name__)

# How many messages to compact in a single LLM call
CHUNK_SIZE = 20

# Redis key pattern for active conversation context cache
CONTEXT_CACHE_KEY = "memory:agent:{agent_id}:context"
# TTL for cached context buffer (seconds) — 24 hours
CONTEXT_CACHE_TTL = 86400


class MemoryCompactor:
    """Extracts semantic memories from raw conversation chunks.

    Usage:
        compactor = MemoryCompactor(providers_manager)
        memories = await compactor.compact(agent_id, messages, session)
    """

    def __init__(self, providers_manager, redis_client=None):
        self.providers = providers_manager
        # Optional raw aioredis client for context buffer caching
        # Pass the .redis attribute of the RedisClient wrapper, not the wrapper itself.
        self._redis = redis_client

    # ─────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────

    async def compact(
        self,
        agent_id: str,
        messages: list[ChatMessage],
        session: AsyncSession,
        conversation_id: str | None = None,
        archive_raw: bool = True,
    ) -> list[SemanticMemory]:
        """Compact a list of messages into SemanticMemory rows.

        1. Optionally archives each message as a ConversationArchive row (Tier 3).
        2. Chunks the messages and extracts semantic facts via LLM (Tier 2).
        3. Persists SemanticMemory objects and returns the created records.
        """
        if archive_raw:
            await self._archive_raw(agent_id, messages, session, conversation_id)

        semantic_records: list[SemanticMemory] = []
        chunks = [messages[i:i + CHUNK_SIZE] for i in range(0, len(messages), CHUNK_SIZE)]

        for chunk in chunks:
            extracted = await self._extract_facts(agent_id, chunk)
            for item in extracted:
                record = SemanticMemory(
                    agent_id=agent_id,
                    memory_type=item.get("memory_type", "fact"),
                    topic=item.get("topic"),
                    summary=item.get("summary", ""),
                    embedding=None,  # populated by a separate embedding pass if needed
                    source_message_ids=item.get("source_message_ids"),
                )
                session.add(record)
                semantic_records.append(record)

        await session.commit()
        logger.info(
            "MemoryCompactor: compacted %d messages → %d semantic memories for agent %s",
            len(messages),
            len(semantic_records),
            agent_id,
        )
        return semantic_records

    async def retrieve_for_context(
        self,
        agent_id: str,
        session: AsyncSession,
        limit: int = 20,
        topic_filter: str | None = None,
    ) -> str:
        """Return a formatted Tier-2 memory block suitable for injection into context."""
        from sqlalchemy import select, desc

        stmt = (
            select(SemanticMemory)
            .where(SemanticMemory.agent_id == agent_id)
            .order_by(desc(SemanticMemory.created_at))
            .limit(limit)
        )
        if topic_filter:
            stmt = stmt.where(SemanticMemory.topic.ilike(f"%{topic_filter}%"))

        result = await session.execute(stmt)
        records = result.scalars().all()

        if not records:
            return ""

        lines = ["[SEMANTIC MEMORY — key facts and prior context]"]
        for r in reversed(records):  # chronological order
            label = f"[{r.memory_type.upper()}]"
            topic = f" ({r.topic})" if r.topic else ""
            lines.append(f"• {label}{topic}: {r.summary}")

        return "\n".join(lines)

    async def cache_context(
        self,
        agent_id: str,
        messages: list[ChatMessage],
    ) -> bool:
        """Write the active context buffer to Redis.

        Key: memory:agent:{agent_id}:context
        Value: JSON list of {role, content} dicts
        TTL: 24 hours

        Returns True on success, False if Redis is unavailable.
        """
        if self._redis is None:
            return False
        key = CONTEXT_CACHE_KEY.format(agent_id=agent_id)
        payload = [
            {"role": m.role, "content": m.content or ""}
            for m in messages
            if m.role != "system"  # skip system messages; they are rebuilt each turn
        ]
        try:
            await self._redis.setex(key, CONTEXT_CACHE_TTL, json.dumps(payload))
            return True
        except Exception as exc:
            logger.debug("MemoryCompactor.cache_context failed: %s", exc)
            return False

    async def get_cached_context(
        self,
        agent_id: str,
    ) -> list[dict] | None:
        """Read the active context buffer from Redis.

        Returns a list of {role, content} dicts, or None if not cached.
        """
        if self._redis is None:
            return None
        key = CONTEXT_CACHE_KEY.format(agent_id=agent_id)
        try:
            raw = await self._redis.get(key)
            if raw:
                return json.loads(raw)
        except Exception as exc:
            logger.debug("MemoryCompactor.get_cached_context failed: %s", exc)
        return None

    # ─────────────────────────────────────────────

    async def _extract_facts(
        self, agent_id: str, messages: list[ChatMessage]
    ) -> list[dict]:
        """Call a cheap LLM to extract structured facts from a message chunk."""
        if not messages:
            return []

        conversation_text = ""
        for m in messages:
            if m.content:
                conversation_text += f"{m.role.upper()}: {m.content}\n"
            if m.tool_calls:
                names = [tc.get("function", {}).get("name") for tc in m.tool_calls]
                conversation_text += f"{m.role.upper()}: [Tools used: {', '.join(names)}]\n"

        prompt = f"""Extract key semantic memories from this conversation excerpt.
Return a JSON array. Each element must have:
  "memory_type": one of "fact" | "decision" | "summary"
  "topic": short topic label (e.g. "user_preferences", "task_outcome", "status_change")
  "summary": concise single-sentence memory (max 120 chars)

Conversation:
{conversation_text}

Respond with ONLY the JSON array — no prose, no markdown fences."""

        provider, model_id = self._pick_provider()
        if provider is None:
            return [{"memory_type": "summary", "topic": "conversation", "summary": conversation_text[:200]}]

        try:
            resp = await provider.complete(
                [ChatMessage(role="user", content=prompt)],
                model=model_id,
                temperature=0.2,
            )
            raw = resp.content or "[]"
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start >= 0 and end > start:
                return json.loads(raw[start:end])
        except Exception as exc:
            logger.debug("MemoryCompactor LLM call failed: %s", exc)

        # Fallback: single summary record
        return [{"memory_type": "summary", "topic": "conversation", "summary": conversation_text[:300]}]

    def _pick_provider(self):
        """Return the cheapest available provider for summarisation."""
        provider_map = getattr(self.providers, "providers", {}) if self.providers else {}
        if "openai" in provider_map:
            return provider_map["openai"], "gpt-4o-mini"
        if "gemini" in provider_map:
            return provider_map["gemini"], "gemini-2.5-flash"
        if "anthropic" in provider_map:
            return provider_map["anthropic"], "claude-haiku-4-20250414"
        return None, None

    async def _archive_raw(
        self,
        agent_id: str,
        messages: list[ChatMessage],
        session: AsyncSession,
        conversation_id: str | None,
    ) -> None:
        """Persist raw messages as ConversationArchive rows (Tier 3)."""
        now = datetime.now(timezone.utc)
        for msg in messages:
            content = msg.content or ""
            if msg.tool_calls:
                content += "\n[tool_calls]" + json.dumps(msg.tool_calls)
            session.add(
                ConversationArchive(
                    agent_id=agent_id,
                    conversation_id=conversation_id,
                    role=msg.role,
                    content=content,
                    meta={"archived_at": now.isoformat()},
                )
            )
        # Flush without commit — caller will commit after adding SemanticMemory rows
        await session.flush()
