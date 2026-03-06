import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.engine import async_session
from app.models.model_config import ModelConfig

async def main():
    async with async_session() as session:
        models = [
            ModelConfig(id="gemini-3.1-pro", provider="gemini", name="Gemini 3.1 Pro", context_window=2097152, is_vision=True),
            ModelConfig(id="gemini-3.1-flash-lite", provider="gemini", name="Gemini 3.1 Flash-Lite", context_window=1048576, is_vision=True),
            ModelConfig(id="gemini-3-pro", provider="gemini", name="Gemini 3 Pro", context_window=2097152, is_vision=True),
            ModelConfig(id="gemini-3-flash-preview", provider="gemini", name="Gemini 3 Flash Preview", context_window=1048576, is_vision=True),
        ]
        
        for m in models:
            await session.merge(m)
        await session.commit()
        print("Gemini 3.x models seeded successfully!")

if __name__ == "__main__":
    asyncio.run(main())
