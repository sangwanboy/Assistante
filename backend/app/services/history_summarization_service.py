"""Background-friendly summarization queue service.

This lightweight implementation stores summary jobs and marks them completed.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.context_memory import SummaryJob


class HistorySummarizationService:
    _instance: "HistorySummarizationService | None" = None

    def __init__(self, session_factory: async_sessionmaker, providers=None):
        self._session_factory = session_factory
        self._providers = providers

    @classmethod
    async def get_instance(cls, session_factory: async_sessionmaker, providers=None) -> "HistorySummarizationService":
        if cls._instance is None:
            cls._instance = cls(session_factory=session_factory, providers=providers)
        return cls._instance

    async def enqueue(
        self,
        thread_id: str,
        trigger: str = "manual",
        task_id: str | None = None,
        agent_id: str | None = None,
    ) -> str:
        now = datetime.now(timezone.utc)
        async with self._session_factory() as session:
            job = SummaryJob(
                thread_id=thread_id,
                task_id=task_id,
                trigger=trigger,
                agent_id=agent_id,
                state="completed",
                updated_at=now,
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)
            return job.id
