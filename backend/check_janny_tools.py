
import asyncio
import json
import sys
from sqlalchemy import select
from app.db.engine import async_session
from app.models.agent import Agent

async def check_janny_tools():
    async with async_session() as session:
        result = await session.execute(select(Agent).where(Agent.is_system == True))
        janny = result.scalar_one_or_none()
        if janny:
            name_safe = janny.name.encode('ascii', 'ignore').decode('ascii')
            print(f"Agent: {name_safe}")
            print(f"Model: {janny.model}")
            tools = json.loads(janny.enabled_tools) if janny.enabled_tools else []
            print(f"Tools: {json.dumps(tools)}")
        else:
            print("Janny not found")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_janny_tools())
