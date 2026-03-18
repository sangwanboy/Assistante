import asyncio
from app.providers.litellm_provider import LiteLLMProvider
from app.schemas.chat import ChatMessage
import litellm

p = LiteLLMProvider('gemini', 'AIzaSyBTzCF7Uh50d5IyvyZmg_pVdOvZngnsM2U')
async def test():
    try:
        async for c in p.stream([ChatMessage(role='user', content='Hello', name='user')], 'gemini/gemini-3-pro-preview'):
            print(c)
        print('SUCCESS')
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(test())