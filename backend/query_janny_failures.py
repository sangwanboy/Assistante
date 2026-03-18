import asyncio
from sqlalchemy import select
from app.db.engine import async_session
from app.models.conversation import Message
from app.models.agent import Agent

async def main():
    async with async_session() as session:
        janny_msgs = []
        stmt = select(Message).where(Message.agent_name.like('%Janny%')).order_by(Message.created_at.desc()).limit(15)
        result = await session.execute(stmt)
        messages = result.scalars().all()
        for m in reversed(messages):
            print(f"[{m.role}] tc_json={m.tool_calls_json}\n  msg: {str(m.content)[:150]}")

if __name__ == "__main__":
    asyncio.run(main())