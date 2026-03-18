"""API routes for task monitoring and management."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.models.task import Task
from app.models.context_memory import TaskStateStoreRecord
from app.schemas.task import TaskOut

router = APIRouter()


@router.get("/active", response_model=list[TaskOut])
async def get_active_tasks(session: AsyncSession = Depends(get_session)):
    """List all pending or running tasks."""
    stmt = (
        select(Task)
        .where(Task.status.in_(["pending", "running"]))
        .order_by(Task.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: str, session: AsyncSession = Depends(get_session)):
    """Get task detail with progress."""
    task = await session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/state/active")
async def get_active_task_states(session: AsyncSession = Depends(get_session)):
    """Return normalized per-thread task states for reactive UI."""
    stmt = (
        select(TaskStateStoreRecord)
        .where(TaskStateStoreRecord.status.in_(["pending", "queued", "running", "working", "waiting"]))
        .order_by(TaskStateStoreRecord.updated_at.desc())
    )
    result = await session.execute(stmt)
    rows = list(result.scalars().all())
    return [
        {
            "task_id": row.task_id,
            "thread_id": row.thread_id,
            "status": row.status,
            "progress": row.progress,
            "assigned_agents": row.assigned_agents,
            "results_summary": row.results_summary,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
        for row in rows
    ]
