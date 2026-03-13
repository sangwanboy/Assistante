import asyncio
from sqlalchemy import text
from app.db.engine import async_session

async def run():
    async with async_session() as s:
        r = await s.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        print(r.fetchall())

asyncio.run(run())
