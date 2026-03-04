import asyncio
import httpx
import json

async def test_chat():
    async with httpx.AsyncClient() as client:
        # First get the agents to find one
        print("Fetching agents...")
        res = await client.get("http://127.0.0.1:8321/api/agents")
        agents = res.json()
        
        if not agents:
            print("No agents found.")
            return
            
        agent = agents[0]
        agent_id = agent["id"]
        
        if not agent.get("model"):
            print("Agent has no model, updating to python model...")
            await client.put(f"http://127.0.0.1:8321/api/agents/{agent_id}", json={"model": "gemini/gemini-2.5-flash"})
        
        print(f"Testing chat with agent {agent['name']} ({agent_id})...")
        
        # Test chat endpoint
        payload = {
            "conversation_id": "test_conv_123",
            "message": "Calculate 25 * 25 and then write the result to a file called test_calc_result.txt using your file_manager tool.",
            "model": "gemini/gemini-2.5-flash"
        }
        
        print("Sending chat request...")
        # using the non-streaming chat or whatever the endpoint name is. Let's see the router.
        # Actually /api/chat is usually non-stream, /api/chat/stream is stream.
        # Let's try /api/chat first. Wait, let's look at the chat endpoint
        # Let's just use the stream endpoint if we don't know
        res = await client.post("http://127.0.0.1:8321/api/chat", json=payload, timeout=60.0)
        
        if res.status_code == 200:
            print("Response:", res.text)
        else:
            print(f"Error {res.status_code}:", res.text)

if __name__ == "__main__":
    asyncio.run(test_chat())
