"""Redis-backed agent registry.

Maintains a fast SET of all non-deleted agent IDs so the agent limit
check (SCARD agents:active >= 60) runs in O(1) without a DB round-trip.

Redis key:   agents:active
Redis type:  SET
Members:     agent UUIDs (strings)

Lifecycle hooks:
  on create  → SADD agents:active {agent_id}
  on delete  → SREM agents:active {agent_id}

Startup sync (called once in lifespan):
  populate SET from DB so restarts are transparent.
"""

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.services.agent_limits import MAX_AGENTS_TOTAL

logger = logging.getLogger(__name__)

REGISTRY_KEY = "agents:active"


class AgentRegistry:
    """Thin wrapper around the Redis agents:active SET."""

    def __init__(self, redis):
        self._redis = redis

    async def register(self, agent_id: str) -> None:
        """Add an agent to the live registry."""
        try:
            await self._redis.sadd(REGISTRY_KEY, agent_id)
        except Exception as exc:
            logger.debug("AgentRegistry.register failed: %s", exc)

    async def unregister(self, agent_id: str) -> None:
        """Remove an agent from the live registry (frees capacity)."""
        try:
            await self._redis.srem(REGISTRY_KEY, agent_id)
        except Exception as exc:
            logger.debug("AgentRegistry.unregister failed: %s", exc)

    async def count(self) -> int:
        """Return the number of registered (non-deleted) agents."""
        try:
            return await self._redis.scard(REGISTRY_KEY)
        except Exception:
            return 0

    async def at_capacity(self) -> bool:
        return await self.count() >= MAX_AGENTS_TOTAL

    async def sync_from_db(self, session: AsyncSession) -> int:
        """Rebuild the Redis SET from the database.

        Safe to call on startup; uses SADD so existing entries are not removed.
        Returns the total number of entries after sync.
        """
        try:
            result = await session.execute(select(Agent.id))
            agent_ids = [row[0] for row in result.all()]
            if agent_ids:
                await self._redis.sadd(REGISTRY_KEY, *agent_ids)
            count = await self._redis.scard(REGISTRY_KEY)
            logger.info(
                "AgentRegistry synced from DB: %d agents registered (limit %d).",
                count,
                MAX_AGENTS_TOTAL,
            )
            return count
        except Exception as exc:
            logger.warning("AgentRegistry.sync_from_db failed: %s", exc)
            return 0
