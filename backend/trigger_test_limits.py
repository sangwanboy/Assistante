import asyncio
import httpx
import json
import time

async def trigger_rate_limits():
    target_id = "gemini/gemini-2.5-flash"
    url_cap = f"http://127.0.0.1:8321/api/models/{target_id}/capability"
    url_chat = "http://127.0.0.1:8321/api/chat/stream"
    
    # 1. Set RPM to 2 for gemini-2.5-flash
    print(f"--- Phase 1: Setting RPM to 2 for {target_id} ---")
    async with httpx.AsyncClient() as client:
        resp = await client.put(url_cap, json={"rpm": 2, "tpm": 100000, "rpd": 100})
        if resp.status_code != 200:
            print(f"Failed to set limit: {resp.text}")
            return
    print("Limits updated successfully.\n")

    # 2. Trigger 3 rapid requests to force a delay on the 3rd request
    print(f"--- Phase 2: Triggering 3 rapid requests to {target_id} ---")
    
    # We need a valid conversation_id. Let's create one or use a dummy.
    async with httpx.AsyncClient(timeout=30) as client:
        # Create a conversation
        conv_resp = await client.post("http://127.0.0.1:8321/api/conversations", json={"title": "Rate Limit Test"})
        conv_id = conv_resp.json()["id"]
        print(f"Created conversation: {conv_id}")

        async def send_req(i):
            print(f"Request {i} starting...")
            start_time = time.time()
            # Note: We need to handle streaming response
            try:
                async with client.stream("POST", url_chat, json={
                    "conversation_id": conv_id,
                    "message": f"Hello {i}, give me a very short response.",
                    "model_string": target_id
                }) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = json.loads(line[6:])
                            if data.get("type") == "error":
                                print(f"Request {i} ERROR: {data.get('error')}")
                            elif data.get("type") == "done":
                                break
                duration = time.time() - start_time
                print(f"Request {i} completed in {duration:.2f}s")
            except Exception as e:
                print(f"Request {i} FAILED: {e}")

        # Fire requests
        await asyncio.gather(
            send_req(1),
            send_req(2),
            send_req(3)
        )

if __name__ == "__main__":
    asyncio.run(trigger_rate_limits())
