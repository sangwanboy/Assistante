import asyncio
from sqlalchemy import select
from app.db.engine import init_database, async_session
from app.models.conversation import Conversation, Message
from app.models.agent import Agent

async def analyze_fixer_loop():
    await init_database()
    async with async_session() as session:
        # Find Fixer agent
        result = await session.execute(select(Agent).where(Agent.name == "Fixer"))
        fixer = result.scalar_one_or_none()
        if not fixer:
            print("Fixer agent not found.")
            return

        # Find conversations for Fixer
        result = await session.execute(
            select(Conversation)
            .where(Conversation.agent_id == fixer.id)
            .order_by(Conversation.updated_at.desc())
            .limit(1)
        )
        conv = result.scalar_one_or_none()
        if not conv:
            print("No conversations for Fixer.")
            return

        print(f"Analyzing Conversation: {conv.id}")
        result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.desc())
            .limit(10)
        )
        messages = result.scalars().all()
        for m in messages:
            print(f"[{m.created_at}] {m.role} ({m.agent_name}): {m.content[:50]}...")

if __name__ == "__main__":
    asyncio.run(analyze_fixer_loop())
