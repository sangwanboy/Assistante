
import asyncio
import sys
from sqlalchemy import select
from app.db.engine import async_session
from app.models.agent import Agent

async def check_agents():
    async with async_session() as session:
        result = await session.execute(select(Agent))
        agents = result.scalars().all()
        for a in agents:
            # Use safe encoding or avoid emojis
            name_safe = a.name.encode('ascii', 'ignore').decode('ascii')
            print(f"Agent: {name_safe}, Model: {a.model}, System: {a.is_system}")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_agents())
