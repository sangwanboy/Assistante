import asyncio
from app.db.engine import async_session
from app.models.agent import Agent
from sqlalchemy import select

async def main():
    async with async_session() as s:
        stmt = select(Agent).where(Agent.status != "deleted")
        res = await s.execute(stmt)
        agents = res.scalars().all()
        print("Agents and their Models:")
        for a in agents:
            print(f"Agent: {a.name}, Model: {a.model}, System: {a.is_system}")

if __name__ == "__main__":
    asyncio.run(main())
