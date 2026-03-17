
import asyncio
from app.providers.registry import ProviderRegistry
from app.config import settings

async def check_models():
    registry = ProviderRegistry()
    try:
        gemini = registry.get("gemini")
        if not gemini.is_available():
            print("Gemini provider not available (missing key?)")
            return
        
        models = await gemini.list_models()
        print("--- Available Gemini Models ---")
        for m in models:
            print(f"ID: {m.id}, Name: {m.name}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_models())
