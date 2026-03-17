import asyncio
from sqlalchemy import select, func
from app.db.engine import init_database, async_session
from app.models.conversation import Message

async def count_messages():
    await init_database()
    async with async_session() as session:
        count = await session.scalar(select(func.count(Message.id)))
        print(f"Total messages in database: {count}")
        
        # Check for Fixer specific
        from app.models.agent import Agent
        res = await session.execute(select(Agent).where(Agent.name == "Fixer"))
        fixer = res.scalar_one_or_none()
        if fixer:
            f_count = await session.scalar(select(func.count(Message.id)).where(Message.agent_name == "Fixer"))
            print(f"Fixer messages: {f_count}")

            # Show last 5
            res = await session.execute(select(Message).where(Message.agent_name == "Fixer").order_by(Message.created_at.desc()).limit(5))
            for m in res.scalars().all():
                print(f"[{m.created_at}] {m.content[:50]}")

if __name__ == "__main__":
    asyncio.run(count_messages())
