"""Agent creation safety limits.

Prevents uncontrolled agent spawning by enforcing:
- MAX_AGENTS_TOTAL: Hard system cap of 60 agents (active + idle + paused).
- MAX_AGENTS_PER_DAY: Maximum agents created in a 24-hour window.

Deleted agents (rows removed from DB / removed from Redis registry) free capacity.
"""

import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent

logger = logging.getLogger(__name__)

# Hard system limit — never allow more than 60 agents to exist simultaneously.
MAX_AGENTS_TOTAL = 60
MAX_AGENTS_PER_DAY = 20


async def get_total_agent_count(session: AsyncSession) -> int:
    """Count all non-deleted agents in the database."""
    result = await session.scalar(
        select(func.count(Agent.id)).where(Agent.status != "deleted")
    )
    return result or 0


async def get_agents_created_today(session: AsyncSession) -> int:
    """Count agents created in the last 24 hours."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    result = await session.scalar(
        select(func.count(Agent.id)).where(Agent.created_at >= cutoff)
    )
    return result or 0


async def can_create_agent(
    session: AsyncSession,
    redis_client=None,
) -> tuple[bool, str]:
    """Check if a new agent can be created.

    Performs a fast Redis pre-check (if client supplied) then a definitive DB check.

    Returns:
        (allowed, reason) — True if allowed, or False with reason string.
    """
    # Fast path: Redis cardinality check
    if redis_client is not None:
        try:
            count = await redis_client.scard("agents:active")
            if count >= MAX_AGENTS_TOTAL:
                logger.warning(
                    "AGENT_LIMIT_REACHED current_agents=%d (Redis fast-check)", count
                )
                return (
                    False,
                    f"AGENT_LIMIT_REACHED: system at capacity ({count}/{MAX_AGENTS_TOTAL}). "
                    "Delete or reuse an existing agent.",
                )
        except Exception as exc:
            logger.debug("Redis agent registry unavailable, falling back to DB: %s", exc)

    # Definitive path: database count
    total = await get_total_agent_count(session)
    if total >= MAX_AGENTS_TOTAL:
        logger.warning("AGENT_LIMIT_REACHED current_agents=%d", total)
        return (
            False,
            f"AGENT_LIMIT_REACHED: system at capacity ({total}/{MAX_AGENTS_TOTAL}). "
            "Delete or reuse an existing agent.",
        )

    today = await get_agents_created_today(session)
    if today >= MAX_AGENTS_PER_DAY:
        return (
            False,
            f"Daily creation limit reached ({today}/{MAX_AGENTS_PER_DAY}). "
            "Try again tomorrow or reuse an existing agent.",
        )

    return True, "OK"


async def find_closest_agent(
    session: AsyncSession,
    required_role: str | None = None,
    required_tools: list[str] | None = None,
) -> Agent | None:
    """Find the closest matching existing agent when creation is blocked.

    Searches by role (partial match) and then by tools overlap.
    """
    import json

    stmt = select(Agent).where(Agent.status.in_(["active", "idle"]))  # noqa: E712

    if required_role:
        stmt = stmt.where(Agent.role.ilike(f"%{required_role}%"))

    result = await session.execute(stmt)
    candidates = list(result.scalars().all())

    if not candidates and required_role:
        # Fallback: search description
        stmt2 = select(Agent).where(
            Agent.status.in_(["active", "idle"]),
            Agent.description.ilike(f"%{required_role}%"),
        )
        result2 = await session.execute(stmt2)
        candidates = list(result2.scalars().all())

    if not candidates:
        return None

    if not required_tools:
        return candidates[0]

    # Score by tool overlap
    best_agent = None
    best_score = -1
    for agent in candidates:
        try:
            agent_tools = json.loads(agent.enabled_tools or "[]")
        except (json.JSONDecodeError, TypeError):
            agent_tools = []
        overlap = len(set(required_tools) & set(agent_tools))
        if overlap > best_score:
            best_score = overlap
            best_agent = agent
    return best_agent
