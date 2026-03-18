import asyncio
import json
from sqlalchemy import select
from app.db.engine import async_session
from app.models.agent import Agent

async def main():
    async with async_session() as session:
        result = await session.execute(select(Agent).where(Agent.is_system == True))
        janny = result.scalar_one_or_none()
        if janny and janny.enabled_tools:
            tools = json.loads(janny.enabled_tools)
            print("Old:", tools)
            # Fix tool names
            new_tools = []
            for t in tools:
                if t == "AgentMessengerTool": new_tools.append("agent_messenger")
                elif t == "SessionStatusTool": new_tools.append("get_session_status")
                else: new_tools.append(t)
            janny.enabled_tools = json.dumps(new_tools)
            await session.commit()
            print("New:", new_tools)

if __name__ == "__main__":
    asyncio.run(main())