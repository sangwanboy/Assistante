import asyncio
from sqlalchemy import select
import sys
import os

# Ensure the backend directory is in the sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.engine import async_session
from app.models.model_config import ModelConfig
from app.models.model_registry import ModelCapability

async def update_gemini_models():
    models_to_add = [
        {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "cw": 1048576, "rpm": 1000, "tpm": 4000000, "rpd": 50000},
        {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "cw": 2097152, "rpm": 150, "tpm": 2000000, "rpd": 10000},
        {"id": "gemini-2.5-flash-lite", "name": "Gemini 2.5 Flash Lite", "cw": 1048576, "rpm": 1000, "tpm": 4000000, "rpd": 50000},
        {"id": "gemini-3-flash-preview", "name": "Gemini 3 Flash Preview", "cw": 1048576, "rpm": 1000, "tpm": 4000000, "rpd": 50000},
        {"id": "gemini-3-pro-preview", "name": "Gemini 3 Pro Preview", "cw": 2097152, "rpm": 150, "tpm": 2000000, "rpd": 10000},
        {"id": "gemini-3.1-flash-preview", "name": "Gemini 3.1 Flash Preview", "cw": 1048576, "rpm": 1000, "tpm": 4000000, "rpd": 50000},
        {"id": "gemini-3.1-flash-lite", "name": "Gemini 3.1 Flash Lite", "cw": 1048576, "rpm": 1000, "tpm": 4000000, "rpd": 50000},
        {"id": "gemini-3.1-pro-preview", "name": "Gemini 3.1 Pro Preview", "cw": 2097152, "rpm": 150, "tpm": 2000000, "rpd": 10000},
    ]

    async with async_session() as session:
        for m in models_to_add:
            # Check ModelConfig
            stmt = select(ModelConfig).where(ModelConfig.id == m["id"], ModelConfig.provider == "gemini")
            result = await session.execute(stmt)
            config = result.scalar_one_or_none()
            if not config:
                config = ModelConfig(id=m["id"], provider="gemini", name=m["name"], context_window=m["cw"], is_vision=True)
                session.add(config)
            
            # Check ModelCapability
            cap_id = f"gemini/{m['id']}"
            stmt_cap = select(ModelCapability).where(ModelCapability.id == cap_id)
            result_cap = await session.execute(stmt_cap)
            cap = result_cap.scalar_one_or_none()
            if not cap:
                cap = ModelCapability(id=cap_id, provider="gemini", model_name=m["id"], rpm=m["rpm"], tpm=m["tpm"], rpd=m["rpd"], context_window=m["cw"])
                session.add(cap)

        await session.commit()
        print("Updated Gemini models successfully in DB.")

if __name__ == "__main__":
    asyncio.run(update_gemini_models())
