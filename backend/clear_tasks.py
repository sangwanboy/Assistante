import asyncio
from sqlalchemy import update
from app.db.engine import init_database, async_session
from app.models.task import Task

async def clear_active_tasks():
    await init_database()
    async with async_session() as session:
        await session.execute(
            update(Task)
            .where(Task.status.in_(["pending", "running"]))
            .values(status="failed", error_message="Terminated due to investigation of infinite loop")
        )
        await session.commit()
        print("Active tasks cleared.")

if __name__ == "__main__":
    asyncio.run(clear_active_tasks())
