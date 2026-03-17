
import asyncio
from sqlalchemy import update
from app.db.engine import async_session
from app.models.agent import Agent

async def fix():
    async with async_session() as session:
        # Update Janny's model
        stmt = (
            update(Agent)
            .where(Agent.is_system)
            .values(model="gemini/gemini-2.5-flash")
        )
        await session.execute(stmt)
        await session.commit()
        print("Updated Janny's model to gemini/gemini-2.5-flash")

if __name__ == "__main__":
    asyncio.run(fix())
