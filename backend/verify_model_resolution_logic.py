
import asyncio
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.agent import Agent
from app.models.conversation import Conversation
from app.services.chat_service import ChatService
from app.providers.registry import ProviderRegistry
from app.tools.registry import ToolRegistry
from app.config import settings

async def verify_resolution():
    # Mocking registries
    pr = ProviderRegistry(settings)
    await pr.initialize()
    tr = ToolRegistry()
    
    async with SessionLocal() as db:
        service = ChatService(pr, tr, db)
        
        # 1. Find Janny Connan
        stmt = select(Agent).where(Agent.name == "Janny Connan")
        res = await db.execute(stmt)
        janny = res.scalar_one_or_none()
        
        if not janny:
            print("Janny Connan not found in DB")
            return

        print(f"Janny Connan Configured Model: {janny.model}")

        # 2. Find or Create a conversation for Janny
        stmt_conv = select(Conversation).where(Conversation.agent_id == janny.id).limit(1)
        res_conv = await db.execute(stmt_conv)
        conv = res_conv.scalar_one_or_none()
        
        if not conv:
            print("No conversation found for Janny, test might be indirect.")
            # We can't easily test stream_chat without a real conversation_id that exists in DB
            return

        print(f"Testing resolution for conversation {conv.id} (Agent: {janny.name})")
        
        # We want to check what model is used inside stream_chat
        # Since we can't easily 'yield' from a script to check internal variables, 
        # let's check the _resolve_provider_and_model logic indirectly or inspect the service.
        
        # Manually trigger the resolution logic as it would be in stream_chat
        effective_model = janny.model if janny else "default/model"
        p_name, m_id, provider, warn = await service._resolve_provider_and_model(effective_model)
        
        print(f"Resolved Provider: {p_name}")
        print(f"Resolved Model ID: {m_id}")
        
        if m_id == "gemini-3.1-flash-lite-preview":
            print("\n✅ SUCCESS: Model resolution correctly identified the preview ID.")
        else:
            print(f"\n❌ FAILURE: Resolved to {m_id} instead of preview ID.")

if __name__ == "__main__":
    asyncio.run(verify_resolution())
