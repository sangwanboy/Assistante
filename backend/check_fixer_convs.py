import asyncio
from sqlalchemy import select
from app.db.engine import init_database, async_session
from app.models.conversation import Conversation, Message

async def check_fixer_conversations():
    await init_database()
    async with async_session() as session:
        # Get conversations for the Fixer agent
        result = await session.execute(
            select(Conversation).where(Conversation.agent_id == "2ec36d50-1599-40b5-8161-126131adcc950")
        )
        convs = result.scalars().all()
        for c in convs:
            # Count messages in each conversation
            m_result = await session.execute(
                select(Message).where(Message.conversation_id == c.id)
            )
            count = len(m_result.scalars().all())
            print(f"Conversation ID: {c.id}, Title: {c.title}, Message Count: {count}")
            
            if count > 100:
                print(f"WARNING: High message count in conversation {c.id}")

if __name__ == "__main__":
    asyncio.run(check_fixer_conversations())
