"""REST API for Heartbeat Schedules."""
import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.models.agent_schedule import AgentSchedule
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate, ScheduleOut

router = APIRouter()


@router.get("", response_model=List[ScheduleOut])
async def list_schedules(
    agent_id: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(AgentSchedule).order_by(AgentSchedule.created_at)
    if agent_id:
        stmt = stmt.where(AgentSchedule.agent_id == agent_id)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=ScheduleOut)
async def create_schedule(
    body: ScheduleCreate,
    session: AsyncSession = Depends(get_session),
):
    sched = AgentSchedule(
        agent_id=body.agent_id,
        name=body.name,
        description=body.description,
        interval_minutes=body.interval_minutes,
        task_config_json=json.dumps(body.task_config),
        is_active=body.is_active,
    )
    session.add(sched)
    await session.commit()
    await session.refresh(sched)
    return sched


@router.put("/{schedule_id}", response_model=ScheduleOut)
async def update_schedule(
    schedule_id: str,
    body: ScheduleUpdate,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(AgentSchedule).where(AgentSchedule.id == schedule_id)
    )
    sched = result.scalar_one_or_none()
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if body.name is not None:
        sched.name = body.name
    if body.description is not None:
        sched.description = body.description
    if body.interval_minutes is not None:
        sched.interval_minutes = body.interval_minutes
    if body.task_config is not None:
        sched.task_config_json = json.dumps(body.task_config)
    if body.is_active is not None:
        sched.is_active = body.is_active

    await session.commit()
    await session.refresh(sched)
    return sched


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(AgentSchedule).where(AgentSchedule.id == schedule_id)
    )
    sched = result.scalar_one_or_none()
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")
    await session.delete(sched)
    await session.commit()
    return {"ok": True}
