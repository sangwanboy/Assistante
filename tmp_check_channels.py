import asyncio
from sqlalchemy import select
from app.db.engine import get_session
from app.models.channel import Channel

async def check_channels():
    async for session in get_session():
        stmt = select(Channel)
        result = await session.execute(stmt)
        channels = result.scalars().all()
        print(f"Total channels: {len(channels)}")
        for c in channels:
            print(f"ID: {c.id}, Name: {c.name}, Orchestration: {c.orchestration_mode}")

if __name__ == "__main__":
    asyncio.run(check_channels())
