import asyncio
import os
import sys

# Add backend dir to sys path so we can import app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.engine import async_session
from app.models.model_config import ModelConfig

async def main():
    async with async_session() as session:
        models = [
            ModelConfig(id="gemini-2.5-pro", provider="gemini", name="Gemini 2.5 Pro", context_window=2097152, is_vision=True),
            ModelConfig(id="gemini-2.5-flash", provider="gemini", name="Gemini 2.5 Flash", context_window=1048576, is_vision=True),
            ModelConfig(id="gemini-2.5-flash-lite-preview-06-17", provider="gemini", name="Gemini 2.5 Flash Lite", context_window=1048576, is_vision=True),
            ModelConfig(id="gemini-2.5-pro-experimental", provider="gemini", name="Gemini 2.5 Pro Exp", context_window=2097152, is_vision=True),
            ModelConfig(id="gemini-2.5-flash-experimental", provider="gemini", name="Gemini 2.5 Flash Exp", context_window=1048576, is_vision=True),
        ]
        
        for m in models:
            await session.merge(m)
        await session.commit()
        print("Latest Gemini 2.5 models seeded successfully!")

if __name__ == "__main__":
    asyncio.run(main())
