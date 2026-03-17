import asyncio
from sqlalchemy import select
from app.db.engine import async_session
from app.models.agent import Agent

async def main():
    async with async_session() as session:
        result = await session.execute(select(Agent))
        agents = result.scalars().all()
        with open("agent_status.txt", "w", encoding="utf-8") as f:
            for a in agents:
                f.write(f"Agent: {a.name}, id: {a.id}, is_system: {a.is_system}\n")

if __name__ == "__main__":
    asyncio.run(main())
