import asyncio
from app.db.engine import async_session
from app.models.model_registry import ModelCapability
from sqlalchemy import select

async def main():
    async with async_session() as s:
        # Check if it exists
        model_id = "gemini/gemini-3.1-flash-lite"
        stmt = select(ModelCapability).where(ModelCapability.id == model_id)
        res = await s.execute(stmt)
        m = res.scalar_one_or_none()
        
        if not m:
            print(f"Model {model_id} not found in registry. Adding it...")
            new_m = ModelCapability(
                id=model_id,
                provider="gemini",
                model_name="gemini-3.1-flash-lite",
                rpm=1000,
                tpm=4000000,
                rpd=1500,
                context_window=1048576,
                is_active=True
            )
            s.add(new_m)
            await s.commit()
            print("Successfully added gemini/gemini-3.1-flash-lite to registry.")
        else:
            print(f"Model {model_id} already exists in registry.")
            if not m.is_active:
                m.is_active = True
                await s.commit()
                print(f"Model {model_id} set to active.")

if __name__ == "__main__":
    asyncio.run(main())
