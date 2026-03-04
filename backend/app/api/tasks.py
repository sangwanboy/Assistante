"""API routes for task monitoring and management."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.models.task import Task
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
