import asyncio
import httpx
from app.config import settings
from app.services.secret_manager import get_secret_manager

async def test_brave():
    get_secret_manager() # warm up
    api_key = get_secret_manager().get_api_key("brave_search")
    print(f"API Key start: {api_key[:5] if api_key else 'None'}")
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
    }
    params = {
        "q": "Iran USA diplomatic signals backchannel communications military escalation latest 24 hours",
        "count": 5,
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://api.search.brave.com/res/v1/web/search", headers=headers, params=params)
            print("Status:", resp.status_code)
            print("Body:", resp.text)
    except Exception as e:
        print("Exception:", e)

if __name__ == "__main__":
    asyncio.run(test_brave())
