import asyncio
from sqlalchemy import select
from app.db.engine import init_database, async_session
from app.models.task import Task
from app.models.agent_schedule import AgentSchedule

async def check_active_activity():
    await init_database()
    async with async_session() as session:
        # Check active tasks
        result = await session.execute(select(Task).where(Task.status.in_(["pending", "running"])))
        tasks = result.scalars().all()
        print(f"Active Tasks: {len(tasks)}")
        for t in tasks:
            print(f"  Task {t.id} [{t.status}]: {t.goal[:50]}... (Agent: {t.assigned_agent_id})")

        # Check active schedules
        result = await session.execute(select(AgentSchedule).where(AgentSchedule.is_active == True))
        schedules = result.scalars().all()
        print(f"Active Schedules: {len(schedules)}")
        for s in schedules:
            print(f"  Schedule {s.id} [{s.name}]: {s.agent_name} every {s.interval_seconds}s")

if __name__ == "__main__":
    asyncio.run(check_active_activity())
