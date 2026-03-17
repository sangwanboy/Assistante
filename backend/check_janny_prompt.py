
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

async def check_janny_prompt():
    async with async_session() as session:
        result = await session.execute(select(Agent).where(Agent.is_system == True))
        janny = result.scalar_one_or_none()
        if janny:
            print(f"Agent: {janny.name}")
            print(f"System Prompt: {janny.system_prompt}")
        else:
            print("Janny not found")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_janny_prompt())
