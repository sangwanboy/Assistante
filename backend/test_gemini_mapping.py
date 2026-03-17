
import asyncio
from app.providers.gemini_provider import GeminiProvider
from app.providers.base import ChatMessage
from app.config import settings

async def test_mapping():
    api_key = settings.gemini_api_key
    provider = GeminiProvider(api_key)
    
    messages = [ChatMessage(role="user", content="hi")]
    # Test mapping
    model_id = "gemini-3.1-flash-lite"
    print(f"Testing model_id: {model_id}")
    
    try:
        # Use complete to avoid streaming complexities for a quick test
        response = await provider.complete(messages, model_id)
        print(f"Success! Response: {response.content}")
    except Exception as e:
        print(f"Failed with error: {e}")

if __name__ == "__main__":
    asyncio.run(test_mapping())
