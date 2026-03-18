"""Task state persistence used by reactive UI and prompt rehydration."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.context_memory import TaskStateStoreRecord


class TaskStateStore:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(
        self,
        task_id: str,
        thread_id: str | None,
        status: str,
        progress: float,
        assigned_agents: list[str] | None = None,
        results_summary: str | None = None,
    ) -> TaskStateStoreRecord:
        stmt = select(TaskStateStoreRecord).where(TaskStateStoreRecord.task_id == task_id)
        res = await self.session.execute(stmt)
        row = res.scalar_one_or_none()

        assigned_agents_json = json.dumps(assigned_agents or [])
        now = datetime.now(timezone.utc)

        if row is None:
            row = TaskStateStoreRecord(
                task_id=task_id,
                thread_id=thread_id or "",
                status=status,
                progress=int(progress or 0),
                assigned_agents=assigned_agents_json,
                results_summary=results_summary,
                updated_at=now,
            )
            self.session.add(row)
        else:
            row.thread_id = thread_id or row.thread_id
            row.status = status
            row.progress = int(progress or 0)
            row.assigned_agents = assigned_agents_json
            if results_summary is not None:
                row.results_summary = results_summary
            row.updated_at = now

        await self.session.commit()
        await self.session.refresh(row)
        return row
