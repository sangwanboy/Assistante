
import asyncio
import json
import sys
import io
from sqlalchemy import select
from app.db.engine import async_session
from app.models.agent import Agent

# Set stdout to handle UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def list_agent_ids():
    async with async_session() as session:
        result = await session.execute(select(Agent))
        agents = result.scalars().all()
        print("Agent IDs and Models:")
        for a in agents:
            name_safe = a.name.encode('ascii', 'ignore').decode('ascii')
            print(f"- {name_safe} (ID: {a.id}, Model: {a.model})")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(list_agent_ids())
