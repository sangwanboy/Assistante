import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.engine import async_session
from app.models.model_config import ModelConfig
from app.models.model_registry import ModelCapability
from sqlalchemy import delete

async def cleanup_models():
    # IDs of models to remove from model_configs
    ids_to_remove = [
        "gemini-2.5-flash-lite-preview-06-17",
        "gemini-2.5-flash-lite", # Redundant with 3.1 
    ]
    
    # IDs to remove from model_registry (provider/id format)
    registry_ids_to_remove = [
        "gemini/gemini-2.5-flash-lite-preview-06-17",
        "gemini/gemini-2.5-flash-lite"
    ]

    async with async_session() as session:
        # Delete from model_configs
        for m_id in ids_to_remove:
            print(f"Removing model_config: {m_id}")
            await session.execute(delete(ModelConfig).where(ModelConfig.id == m_id))
            
        # Delete from model_registry
        for r_id in registry_ids_to_remove:
            print(f"Removing model_registry entry: {r_id}")
            await session.execute(delete(ModelCapability).where(ModelCapability.id == r_id))
            
        await session.commit()
        print("Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(cleanup_models())
