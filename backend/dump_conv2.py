import asyncio
from sqlalchemy import select
from app.db.engine import async_session
from app.models.conversation import Message
import json

async def main():
    async with async_session() as session:
        # Get latest 15 messages
        stmt = select(Message).order_by(Message.created_at.desc()).limit(15)
        result = await session.execute(stmt)
        messages = list(reversed(result.scalars().all()))
        for m in messages:
            content_safe = (m.content or '').encode('ascii', 'ignore').decode()[:80].replace('\n', ' ')
            if m.tool_calls_json:
                print(f"[{m.role}] HAS_TOOL_CALLS: {m.tool_calls_json[:100]}...")
            else:
                print(f"[{m.role}] {content_safe}")

if __name__ == "__main__":
    asyncio.run(main())