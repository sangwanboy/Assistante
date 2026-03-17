import asyncio
import json
from sqlalchemy import select
from app.db.engine import async_session
from app.models.conversation import Message, Conversation

async def main():
    async with async_session() as session:
        # Get the newest heartbeat conversation
        result = await session.execute(
            select(Conversation).filter(Conversation.title.like("__heartbeat_%")).order_by(Conversation.updated_at.desc()).limit(1)
        )
        conv = result.scalar_one_or_none()
        if not conv:
            print("No heartbeat conversations found.")
            return
            
        print(f"Conversation: {conv.id}")
        
        # Get messages for this conversation
        result = await session.execute(
            select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at.asc())
        )
        messages = result.scalars().all()
        
        for m in messages:
            print(f"Role: {m.role}")
            if m.content:
                print(f"Content: {m.content[:100]}...")
            if m.tool_calls_json:
                print(f"Tool Calls: {m.tool_calls_json}")
            print("-" * 40)

if __name__ == "__main__":
    asyncio.run(main())
