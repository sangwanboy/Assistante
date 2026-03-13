
import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.db.engine import async_session, init_database
from app.services.model_registry_service import ModelRegistryService
from sqlalchemy import select
from app.models.model_registry import ModelCapability

async def test():
    await init_database()
    async with async_session() as db:
        # 1. Check what's in DB
        res = await db.execute(select(ModelCapability).where(ModelCapability.model_name == "gemini-2.5-flash"))
        cap = res.scalar_one_or_none()
        if cap:
            print(f"DB Record: ID={cap.id}, Name={cap.model_name}, RPM={cap.rpm}, RPD={cap.rpd}")
        else:
            print("No DB record found for gemini-2.5-flash")
            
        # 2. Test Resolution for short name
        resolved = await ModelRegistryService.get_effective_capabilities("gemini-2.5-flash", db)
        print(f"Resolved (short name): RPM={resolved['rpm']}, RPD={resolved['rpd']}")
        
        # 3. Test Resolution for full ID
        resolved_full = await ModelRegistryService.get_effective_capabilities("gemini/gemini-2.5-flash", db)
        print(f"Resolved (full ID): RPM={resolved_full['rpm']}, RPD={resolved_full['rpd']}")

if __name__ == "__main__":
    asyncio.run(test())
