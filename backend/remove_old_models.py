import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import delete
from app.db.engine import async_session
from app.models.model_config import ModelConfig

async def main():
    async with async_session() as session:
        # Delete models older than 2.5
        old_model_ids = [
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-1.5-flash-8b",
            "learnlm-1.5-pro-experimental",
            "gemini-2.0-flash-exp",
            "gemini-2.0-flash-thinking-exp-01-21",
            "gemini-exp-1206",
        ]
        
        for model_id in old_model_ids:
            stmt = delete(ModelConfig).where(ModelConfig.id == model_id)
            await session.execute(stmt)
            
        await session.commit()
        print("Old models removed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
