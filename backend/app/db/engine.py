import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.base import Base


DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "assitance.db")
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_database():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Migrate: add new columns if they don't exist (SQLite doesn't support IF NOT EXISTS for columns)
        new_agent_cols = [
            ("personality_tone", "TEXT"),
            ("personality_traits", "TEXT"),
            ("communication_style", "TEXT"),
            ("enabled_tools", "TEXT"),
            ("reasoning_style", "TEXT"),
            ("memory_context", "TEXT"),
            ("memory_instructions", "TEXT"),
        ]
        for col_name, col_type in new_agent_cols:
            try:
                await conn.execute(
                    __import__("sqlalchemy").text(f"ALTER TABLE agents ADD COLUMN {col_name} {col_type}")
                )
            except Exception:
                pass  # Column already exists
                
        # Migrate: add agent_id to conversations
        try:
            await conn.execute(
                __import__("sqlalchemy").text(f"ALTER TABLE conversations ADD COLUMN agent_id VARCHAR")
            )
        except Exception:
            pass


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
