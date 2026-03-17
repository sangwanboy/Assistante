import asyncio
from sqlalchemy import select
from app.db.engine import init_database, async_session
from app.models.agent import Agent
from app.models.conversation import Conversation, Message

async def find_fixer_and_convs():
    await init_database()
    async with async_session() as session:
        # Find Fixer agent
        result = await session.execute(
            select(Agent).where(Agent.name.like("%Fixer%"))
        )
        agents = result.scalars().all()
        for a in agents:
            print(f"Agent ID: {a.id}, Name: {a.name}")
            
            # Find conversations for this agent
            c_result = await session.execute(
                select(Conversation).where(Conversation.agent_id == a.id)
            )
            convs = c_result.scalars().all()
            for c in convs:
                m_result = await session.execute(
                    select(Message).where(Message.conversation_id == c.id)
                )
                messages = m_result.scalars().all()
                print(f"  Conversation ID: {c.id}, Title: {c.title}, Messages: {len(messages)}")
                
                # If messages > 0, show the roles of the last 10
                if messages:
                    last_10 = messages[-10:]
                    roles = [m.role for m in last_10]
                    print(f"    Last 10 roles: {roles}")

if __name__ == "__main__":
    asyncio.run(find_fixer_and_convs())
