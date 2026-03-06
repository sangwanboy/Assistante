import asyncio
import sys
import os
sys.path.insert(0, os.getcwd())
from app.db.engine import async_session
from sqlalchemy import select
from app.models.agent import Agent
from app.schemas.agent import AgentOut

async def check():
    async with async_session() as session:
        result = await session.execute(select(Agent))
        agents = result.scalars().all()
        for a in agents:
            print(f"Checking agent: {a.name}")
            try:
                AgentOut.model_validate(a, from_attributes=True)
                print("Valid")
            except Exception as e:
                print("Error:", e)
asyncio.run(check())
