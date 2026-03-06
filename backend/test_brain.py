"""Test script for file-based agent brain."""
import asyncio
from app.db.engine import async_session
from sqlalchemy import select
from app.models.agent import Agent
from app.services.chat_service import ChatService
from app.providers.registry import ProviderRegistry
from app.tools.registry import ToolRegistry
from app.tools.memory_tool import SaveMemoryTool, WriteDailyLogTool
from app.config import settings

async def test_brain():
    async with async_session() as session:
        # Get Janny
        result = await session.execute(select(Agent).where(Agent.name == "Janny"))
        janny = result.scalar_one_or_none()
        
        if not janny:
            print("Janny not found!")
            return
            
        print(f"=== Testing Brain for {janny.name} ===\n")
        
        # Test 1: Prompt Generation
        print("--- 1. Testing _build_agent_prompt ---")
        chat_svc = ChatService(ProviderRegistry(settings), ToolRegistry(), session)
        prompt = chat_svc._build_agent_prompt(janny)
        print("PROMPT LENGTH:", len(prompt), "chars")
        print("\n--- SNIPPET ---")
        print(prompt[:500] + "\n...\n" + prompt[-500:])
        print("--------------------------------------\n")
        
        # Test 2: Tools (Save Memory)
        print("--- 2. Testing SaveMemoryTool ---")
        save_tool = SaveMemoryTool()
        result = await save_tool.execute(
            fact="The user has successfully replaced my database brain with a file-based memory system.",
            _agent_id=janny.id,
            _session=session
        )
        print("SaveMemoryTool Result:", result)
        
        # Test 3: Tools (Write Daily Log)
        print("\n--- 3. Testing WriteDailyLogTool ---")
        log_tool = WriteDailyLogTool()
        result = await log_tool.execute(
            entry="Upgraded my brain architecture to use file-based memory. I am now fully portable.",
            _agent_id=janny.id,
            _session=session
        )
        print("WriteDailyLogTool Result:", result)
        
        # Test 4: Re-check Prompt Generation (should include new memory and log)
        print("\n--- 4. Checking Prompt after insertions ---")
        prompt2 = chat_svc._build_agent_prompt(janny)
        print("PROMPT LENGTH CHANGED:", len(prompt2) > len(prompt))
        print("Contains new fact?", "The user has successfully replaced my database brain" in prompt2)
        print("Contains new log?", "Upgraded my brain architecture to use file-based memory" in prompt2)

asyncio.run(test_brain())
