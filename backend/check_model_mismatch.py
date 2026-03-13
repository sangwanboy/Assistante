
from app.db.session import SessionLocal
from app.models.agent import Agent
from app.models.model_config import ModelConfig
import asyncio
import json

async def check():
    async with SessionLocal() as db:
        # Check Agent
        result = await db.execute(Agent.__table__.select().where(Agent.name == "Janny Connan"))
        agent = result.fetchone()
        if agent:
            print(f"Agent: {agent.name}")
            print(f"Provider: {agent.provider}")
            print(f"Model ID: {agent.model}")
        else:
            print("Agent 'Janny Connan' not found")

        # Check Model Config in DB
        result = await db.execute(ModelConfig.__table__.select().where(ModelConfig.id == agent.model))
        model_cfg = result.fetchone()
        if model_cfg:
            print(f"\nModelConfig ID: {model_cfg.id}")
            print(f"ModelConfig Name: {model_cfg.name}")
            print(f"ModelConfig Provider: {model_cfg.provider}")
        else:
            print(f"\nModelConfig '{agent.model}' not found in DB")

if __name__ == "__main__":
    asyncio.run(check())
