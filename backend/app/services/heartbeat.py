"""Proactive Heartbeat Service: scheduled autonomous background tasks for agents.

Uses asyncio-based scheduling (no extra dependencies).
Supports cron-like expressions and interval-based tasks.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.services.chat_service import ChatService
    from app.providers.registry import ProviderRegistry
    from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class HeartbeatService:
    """Background service that wakes agents on a schedule and runs their tasks."""

    _instance: HeartbeatService | None = None

    def __init__(self) -> None:
        self._running = False
        self._task: asyncio.Task | None = None
        self._provider_registry = None
        self._tool_registry = None
        self._session_factory = None

    @classmethod
    def get_instance(cls) -> "HeartbeatService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def configure(self, provider_registry, tool_registry, session_factory) -> None:
        self._provider_registry = provider_registry
        self._tool_registry = tool_registry
        self._session_factory = session_factory

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("HeartbeatService started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("HeartbeatService stopped")

    async def _loop(self) -> None:
        """Check schedules every 60 seconds."""
        while self._running:
            try:
                await self._tick()
            except Exception as exc:
                logger.error("HeartbeatService tick error: %s", exc, exc_info=True)
            await asyncio.sleep(60)

    async def _tick(self) -> None:
        """Load all active schedules, fire any that are due."""
        if self._session_factory is None:
            return
        from app.models.agent_schedule import AgentSchedule
        from app.models.agent import Agent

        async with self._session_factory() as session:
            now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
            result = await session.execute(
                select(AgentSchedule).where(AgentSchedule.is_active == True)
            )
            schedules = result.scalars().all()

            for sched in schedules:
                if self._is_due(sched, now):
                    await self._fire(sched, session)

    def _is_due(self, sched, now: datetime) -> bool:
        """Simple interval check: fire if interval_minutes have elapsed since last_run."""
        interval = sched.interval_minutes or 60
        if sched.last_run is None:
            return True
        last = sched.last_run
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        elapsed = (now - last).total_seconds() / 60
        return elapsed >= interval

    async def _fire(self, sched, session: AsyncSession) -> None:
        """Execute the scheduled task for an agent."""
        from app.models.agent import Agent
        from app.models.agent_schedule import AgentSchedule
        from app.services.chat_service import ChatService

        agent_result = await session.execute(
            select(Agent).where(Agent.id == sched.agent_id)
        )
        agent = agent_result.scalar_one_or_none()
        if not agent:
            return

        logger.info(
            "Heartbeat firing schedule '%s' for agent '%s'", sched.name, agent.name
        )

        task_config = json.loads(sched.task_config_json or "{}")
        prompt = task_config.get(
            "prompt",
            f"Heartbeat tick: {sched.name}. Please run your scheduled task.",
        )

        chat_svc = ChatService(
            provider_registry=self._provider_registry,
            tool_registry=self._tool_registry,
            session=session,
        )

        # Find or create a dedicated heartbeat conversation for this agent
        from app.models.conversation import Conversation
        conv_result = await session.execute(
            select(Conversation).where(
                Conversation.agent_id == sched.agent_id,
                Conversation.title == f"__heartbeat_{sched.id}__",
            )
        )
        conv = conv_result.scalar_one_or_none()
        if conv is None:
            import uuid
            from app.models.conversation import Conversation as Conv
            conv = Conv(
                id=str(uuid.uuid4()),
                title=f"__heartbeat_{sched.id}__",
                agent_id=sched.agent_id,
                model=agent.model or "gemini/gemini-2.5-flash",
            )
            session.add(conv)
            await session.commit()
            await session.refresh(conv)

        # Run as a non-streaming chat call
        try:
            await chat_svc.chat(
                conversation_id=conv.id,
                user_message=prompt,
                model=agent.model or "gemini/gemini-2.5-flash",
            )
        except Exception as exc:
            logger.error("Heartbeat task failed for agent %s: %s", agent.name, exc)

        # Update last_run
        from datetime import timezone
        sched.last_run = datetime.now(timezone.utc)
        await session.commit()
