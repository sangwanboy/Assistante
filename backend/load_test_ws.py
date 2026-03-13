
import asyncio
import json
import time
import uuid
import websockets
import httpx

async def test_delay_and_block_ws():
    target_id = "gemini/gemini-2.5-flash"
    base_url = "http://127.0.0.1:8323"
    ws_url_template = "ws://127.0.0.1:8323/ws/chat/{conv_id}"
    url_cap = f"{base_url}/api/models/{target_id}/capability"
    
    # 1. Set RPM=1, RPD=100 (No block, only delay)
    async with httpx.AsyncClient() as client:
        await client.put(url_cap, json={"rpm": 1, "tpm": 100000, "rpd": 100})
    print(f"--- Setting limits: RPM=1, RPD=100 for {target_id} ---")
    
    conv_id = str(uuid.uuid4())
    print(f"Conversation: {conv_id}")

    async def run_single_request(label):
        print(f"[{label}] Connecting to WS...")
        start = time.time()
        try:
            async with websockets.connect(ws_url_template.format(conv_id=conv_id)) as ws:
                await ws.send(json.dumps({
                    "type": "message",
                    "content": f"Hi from {label}",
                    "model": target_id
                }))
                
                async for message in ws:
                    data = json.loads(message)
                    if data.get("type") == "done":
                        duration = time.time() - start
                        print(f"[{label}] SUCCESS in {duration:.2f}s")
                        return "allowed"
                    if data.get("type") == "error":
                        print(f"[{label}] BLOCKED: {data.get('error')}")
                        return "blocked"
        except Exception as e:
            print(f"[{label}] FAILED: {str(e)}")
            return "error"

    print("\n--- Starting Sequential Sequence (Triggering RPM Layer) ---")
    results = []
    
    # R1 should pass immediately
    results.append(await run_single_request("R1"))
    
    # R2 should pass immediately too because RPM is per minute, but wait...
    # If I run them sequentially, R1 takes ~2s. R2 starts after. 
    # The bucket for RPM key has 1 entry. 
    # If I run R2 IMMEDIATELY after R1, it should DELAY for 5s because 1 entry exists in the last 60s.
    
    print("\n--- Starting R2 (Expecting Delay) ---")
    results.append(await run_single_request("R2"))

    print("\n--- Summary ---")
    for i, res in enumerate(results):
        print(f"R{i+1}: {res}")

if __name__ == "__main__":
    asyncio.run(test_delay_and_block_ws())
