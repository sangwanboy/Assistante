import asyncio
from sqlalchemy import select
from app.db.engine import async_session
from app.models.model_registry import ModelCapability

async def check():
    async with async_session() as db:
        # Check all models in registry
        stmt = select(ModelCapability)
        res = await db.execute(stmt)
        models = res.scalars().all()
        print(f"Found {len(models)} models in registry:")
        for m in models:
            print(f"- ID: {m.id}, Name: {m.model_name}, RPM: {m.rpm}, RPD: {m.rpd}")
            
        # specifically check gemini/gemini-2.5-flash
        target = "gemini/gemini-2.5-flash"
        stmt_target = select(ModelCapability).where(ModelCapability.id == target)
        res_target = await db.execute(stmt_target)
        cap = res_target.scalar_one_or_none()
        if cap:
            print(f"\nTarget {target} found! Effective RPM: {cap.rpm}, RPD: {cap.rpd}")
        else:
            print(f"\nTarget {target} NOT FOUND in DB.")

if __name__ == "__main__":
    asyncio.run(check())
