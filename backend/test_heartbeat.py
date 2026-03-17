import asyncio
import httpx

async def test_heartbeat():
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Create a new conversation with agent Janny Coneon (system orchestrator)
        conversations_resp = await client.post("http://localhost:8322/api/conversations", json={
            "title": "Test Heartbeat Tool"
        })
        conv_id = conversations_resp.json()["id"]
        
        print(f"Sending message to conversation {conv_id}...")
        resp = await client.post("http://localhost:8322/api/chat", json={
            "conversation_id": conv_id,
            "message": "create a heartbeat every 5 minutes for market checks",
            "model": "gemini/gemini-2.5-flash",
            "temperature": 0.5
        })
        
        print("Response:", resp.text)

if __name__ == "__main__":
    asyncio.run(test_heartbeat())
