import asyncio
import websockets
import json

async def test():
    uri = "ws://127.0.0.1:8321/ws/chat/65951c27-d016-43b9-a034-71bc5dcaba20"
    try:
        async with websockets.connect(uri) as ws:
            req = {
                "type": "message",
                "content": "Hello everyone, please introduce yourselves.",
                "is_group": True
            }
            await ws.send(json.dumps(req))
            while True:
                try:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    if data.get("type") == "error":
                        print("ERROR:", data)
                        break
                    
                    if data.get("type") == "agent_turn_start":
                        print(f"\n--- {data.get('agent_name')} ---")
                    elif data.get("type") == "chunk":
                        print(data.get("delta", ""), end="", flush=True)
                    elif data.get("type") == "done":
                        print("\nDONE!")
                        break
                except Exception as e:
                    print("Recv Error:", e)
                    break
    except Exception as e:
        print("Connect Error:", e)

asyncio.run(test())
