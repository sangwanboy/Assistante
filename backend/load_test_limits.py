import asyncio
import httpx
import json
import time

async def test_delay_and_block():
    target_id = "gemini/gemini-2.5-flash"
    url_cap = f"http://127.0.0.1:8322/api/models/{target_id}/capability"
    url_chat = "http://127.0.0.1:8322/api/chat/stream"
    
    # 1. Set very low limits to force enforcement
    # RPM=2, RPD=5
    print(f"--- Setting limits: RPM=1, RPD=3 for {target_id} ---")
    async with httpx.AsyncClient() as client:
        await client.put(url_cap, json={"rpm": 1, "tpm": 100000, "rpd": 3})
        
        # Create a conversation
        conv_resp = await client.post("http://127.0.0.1:8321/api/conversations", json={"title": "Load Test"})
        conv_id = conv_resp.json()["id"]
        print(f"Conversation: {conv_id}")

    async def send_request(label):
        print(f"[{label}] Sending request...")
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=40) as client:
                async with client.stream("POST", url_chat, json={
                    "conversation_id": conv_id,
                    "message": "Say 'Test'",
                    "model_string": target_id
                }) as resp:
                    full_text = ""
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            data = json.loads(line[6:])
                            if data.get("type") == "error":
                                print(f"[{label}] ERROR: {data.get('error')}")
                                return "blocked"
                            if data.get("type") == "chunk":
                                full_text += data.get("delta", "")
                    
                    end = time.time()
                    print(f"[{label}] Success in {end - start:.2f}s")
                    return "allowed"
        except Exception as e:
            print(f"[{label}] FAILED: {e}")
            return "failed"

    # Sequence:
    # 1. First request -> Allowed
    # 2. Second request immediately -> Should DELAY (due to RPM=1)
    # 3. Third request -> Should DELAY then ALLOW
    # 4. Fourth request -> Should BLOCK (due to RPD=3)
    
    print("\n--- Starting Sequence ---")
    results = []
    
    # R1
    results.append(await send_request("R1"))
    
    # R2 (Immediate - should delay 5s)
    results.append(await send_request("R2"))
    
    # R3
    results.append(await send_request("R3"))
    
    # R4 (Should block at RPD=3)
    results.append(await send_request("R4"))
    
    print("\n--- Summary ---")
    for i, r in enumerate(results):
        print(f"R{i+1}: {r}")

if __name__ == "__main__":
    asyncio.run(test_delay_and_block())
