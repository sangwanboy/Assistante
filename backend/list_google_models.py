import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.getcwd())

from app.services.secret_manager import get_secret_manager
from google import genai

async def list_models():
    sm = get_secret_manager()
    api_key = sm.get_api_key("gemini")
    if not api_key:
        print("Error: Gemini API key not found.")
        return

    try:
        client = genai.Client(api_key=api_key)
        print("Fetching available models...")
        for model in client.models.list():
            if "imagen" in model.name.lower():
                print(f"Model Name: {model.name}")
                try:
                    # Some versions use different attributes
                    print(f"  ID: {model.name}")
                    print(f"  Description: {getattr(model, 'description', 'N/A')}")
                except Exception:
                    pass
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    asyncio.run(list_models())
