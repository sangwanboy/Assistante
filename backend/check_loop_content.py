import asyncio
from sqlalchemy import select
from app.db.engine import init_database, async_session
from app.models.conversation import Message

async def check_loop_content():
    await init_database()
    async with async_session() as session:
        # Get last 20 messages from the problematic conversation
        result = await session.execute(
            select(Message)
            .where(Message.conversation_id == "312ff829-9dc2-4b79-8455-e30237ec4959")
            .order_by(Message.created_at.desc())
            .limit(20)
        )
        msgs = result.scalars().all()
        for m in reversed(msgs):
            print(f"Role: {m.role}, Content: {m.content[:500]}")
            if m.tool_calls_json:
                print(f"  Tool Calls: {m.tool_calls_json}")

if __name__ == "__main__":
    asyncio.run(check_loop_content())
