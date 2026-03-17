import asyncio
from sqlalchemy import select
from app.db.engine import init_database, async_session
from app.models.task import Task

async def check_tasks():
    await init_database()
    async with async_session() as session:
        result = await session.execute(select(Task).where(Task.status.in_(["pending", "running"])))
        tasks = result.scalars().all()
        for t in tasks:
            print(f"Task ID: {t.id}, Agent: {t.assigned_agent_id}, Status: {t.status}, Goal: {t.goal[:100]}...")

if __name__ == "__main__":
    asyncio.run(check_tasks())
