import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import delete, select
from app.db.engine import init_database, async_session
from app.models.conversation import Message, Conversation
from app.models.task import Task

async def purge_loop_artifacts():
    await init_database()
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=60)
    async with async_session() as session:
        # Delete messages from the last hour (safetime)
        stmt = delete(Message).where(Message.created_at > cutoff)
        result = await session.execute(stmt)
        print(f"Deleted {result.rowcount} messages from the last hour.")

        # Fail any tasks from the last hour
        stmt = select(Task).where(Task.status.in_(["pending", "running"]))
        tasks = await session.execute(stmt)
        for t in tasks.scalars().all():
            t.status = "failed"
            t.error_message = "[Purged for loop prevention]"
        
        await session.commit()
        print("Tasks cleared and committed.")

if __name__ == "__main__":
    asyncio.run(purge_loop_artifacts())
