import asyncio
from sqlalchemy import select
from app.db.engine import init_database, async_session
from app.models.task import Task

async def list_all_tasks():
    await init_database()
    async with async_session() as session:
        result = await session.execute(select(Task).order_by(Task.updated_at.desc()))
        tasks = result.scalars().all()
        print(f"Total Tasks: {len(tasks)}")
        for t in tasks:
            print(f"ID: {t.id} | Agent: {t.assigned_agent_id} | Status: {t.status} | Stage: {t.lifecycle_stage} | Goal: {t.goal[:50]}...")
            if t.error_message:
                print(f"  Error: {t.error_message}")

if __name__ == "__main__":
    asyncio.run(list_all_tasks())
