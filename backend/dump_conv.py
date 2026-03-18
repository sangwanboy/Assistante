import asyncio
from sqlalchemy import select
from app.db.engine import async_session
from app.models.conversation import Message

async def main():
    async with async_session() as session:
        # Get latest 100 messages
        stmt = select(Message).order_by(Message.created_at.desc()).limit(100)
        result = await session.execute(stmt)
        messages = list(reversed(result.scalars().all()))
        for m in messages:
            if m.tool_calls_json:
                print(f"[{m.role}] (ID:{m.id}) HAS_TOOL_CALLS: {m.tool_calls_json}")
            elif m.role == 'tool':
                print(f"[tool] (ID:{m.id}) {m.content[:100].strip()}")
            elif 'update' in (m.content or '') or 'Manager' in (m.content or ''):
                print(f"[{m.role}] {m.content[:100].strip()}")

if __name__ == "__main__":
    asyncio.run(main())