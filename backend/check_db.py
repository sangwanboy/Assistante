
import asyncio
from sqlalchemy import select
from app.db.engine import async_session
from app.models.agent import Agent
from app.models.channel import Channel
from app.models.channel_agent import ChannelAgent

async def check():
    async with async_session() as session:
        # Check models
        from app.models.model_config import ModelConfig
        from app.models.model_registry import ModelCapability
        
        res = await session.execute(select(ModelConfig))
        configs = res.scalars().all()
        print(f"\n--- Model Configs ---")
        for mc in configs:
            print(f"ID: {mc.id}, Provider: {mc.provider}, Name: {mc.name}")
            
        res = await session.execute(select(ModelCapability))
        caps = res.scalars().all()
        print(f"\n--- Model Capabilities ---")
        for cap in caps:
            print(f"ID: {cap.id}, Model: {cap.model_name}")

        # Check channels
        res = await session.execute(select(Channel))
        channels = res.scalars().all()
        print(f"\n--- Channels ---")
        for c in channels:
            print(f"Name: {c.name}, ID: {c.id}, Mode: {c.orchestration_mode}")
            
            # Check agents in this channel
            res_ca = await session.execute(select(Agent.name).join(ChannelAgent).where(ChannelAgent.channel_id == c.id))
            cas = res_ca.scalars().all()
            print(f"  Agents: {', '.join(cas)}")

if __name__ == "__main__":
    asyncio.run(check())
