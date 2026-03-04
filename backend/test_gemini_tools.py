import asyncio
from app.providers.gemini_provider import GeminiProvider
from app.providers.base import ChatMessage
import os
from dotenv import load_dotenv

load_dotenv()

async def test():
    api_key = os.getenv("ASSITANCE_GEMINI_API_KEY")
    provider = GeminiProvider(api_key=api_key)
    
    messages = [
        ChatMessage(role="user", content="Test message"),
        ChatMessage(role="user", content="[Analyst Agent]: "),
        ChatMessage(role="tool", content="Tool result output", tool_call_id="call_123")
    ]
    
    try:
        async for chunk in provider.stream(messages, "gemini-2.5-flash", tools=[{"name": "test_tool", "description": "test", "parameters": {}}]):
            print(chunk.delta)
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test())
