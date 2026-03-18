import asyncio, websockets, json
async def test():
    async with websockets.connect('ws://127.0.0.1:8321/ws/chat/09ef6d91-71d0-4244-93ab-8d37fd014a05') as ws:
        await ws.send(json.dumps({'type':'message','content':'Hello Janny','model':'gemini/gemini-2.5-flash','is_group':False}))
        while True:
            msg = await ws.recv()
            print(msg)
            if 'error' in msg or 'done' in msg:
                break
asyncio.run(test())
