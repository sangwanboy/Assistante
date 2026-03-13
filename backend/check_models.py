import asyncio
from app.db.engine import async_session
from app.models.model_registry import ModelCapability
from sqlalchemy import select

async def main():
    async with async_session() as s:
        stmt = select(ModelCapability)
        res = await s.execute(stmt)
        models = res.scalars().all()
        print("Active Models in Registry:")
        for m in models:
            print(f"ID: {m.id}, Name: {m.model_name}, RPM: {m.rpm}, TPM: {m.tpm}")

if __name__ == "__main__":
    asyncio.run(main())
