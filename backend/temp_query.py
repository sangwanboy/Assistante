import asyncio; import httpx; async def f():
 async with httpx.AsyncClient() as c:
  r = await c.post('http://127.0.0.1:8321/api/chat', json={'message': 'test', 'model': 'gemini/gemini-3-pro-preview'}); print(r.status_code); print(r.text)
asyncio.run(f())
