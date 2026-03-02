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
            ("api_key", "TEXT"),
            ("is_system", "BOOLEAN DEFAULT 0"),
        ]
        import sqlalchemy
        from sqlalchemy import select, func
        for col_name, col_type in new_agent_cols:
            try:
                await conn.execute(sqlalchemy.text(f"ALTER TABLE agents ADD COLUMN {col_name} {col_type}"))
            except Exception:
                pass  # Column already exists
                
        # Migrate: add agent_id to conversations
        try:
            await conn.execute(sqlalchemy.text(f"ALTER TABLE conversations ADD COLUMN agent_id VARCHAR"))
        except Exception:
            pass

        # Migrate: add channel_id to conversations
        try:
            await conn.execute(sqlalchemy.text(f"ALTER TABLE conversations ADD COLUMN channel_id VARCHAR"))
        except Exception:
            pass

        # Migrate: add agent_id and channel_id to workflows
        for col_name in ["agent_id", "channel_id"]:
            try:
                await conn.execute(sqlalchemy.text(f"ALTER TABLE workflows ADD COLUMN {col_name} VARCHAR"))
            except Exception:
                pass
            
    # Import models to ensure they are created by Base.metadata.create_all
    from app.models.model_config import ModelConfig
    from app.models.agent import Agent, new_id
    from app.models.channel import Channel
    from app.models.channel_agent import ChannelAgent
    
    # Seeding defaults
    async with async_session() as session:
        # Seed ModelConfigs
        stmt = select(func.count(ModelConfig.id))
        count = await session.scalar(stmt)
        if count == 0:
            default_models = [
                ModelConfig(id="gemini-2.5-flash", provider="gemini", name="Gemini 2.5 Flash", context_window=1048576, is_vision=True),
                ModelConfig(id="gemini-2.5-flash-lite-preview-06-17", provider="gemini", name="Gemini Flash Lite", context_window=1048576, is_vision=True),
                ModelConfig(id="gemini-2.5-pro", provider="gemini", name="Gemini 2.5 Pro", context_window=2097152, is_vision=True),
                ModelConfig(id="claude-3-5-sonnet-20241022", provider="anthropic", name="Claude 3.5 Sonnet", context_window=200000, is_vision=True),
                ModelConfig(id="gpt-4o", provider="openai", name="GPT-4o", context_window=128000, is_vision=True),
            ]
            session.add_all(default_models)
            await session.commit()
            
        # Seed Announcements Channel
        stmt = select(func.count(Channel.id)).where(Channel.is_announcement == True)
        announcement_count = await session.scalar(stmt)
        if announcement_count == 0:
            announcements = Channel(
                id=new_id(),
                name="Announcements",
                description="Broadcast messages to all active agents.",
                is_announcement=True,
            )
            session.add(announcements)
            await session.commit()
            
        # Seed Main Agent
        stmt = select(func.count(Agent.id)).where(Agent.is_system == True)
        main_count = await session.scalar(stmt)
        if main_count == 0:
            main_agent = Agent(
                id=new_id(),
                name="Main Agent",
                description="System Orchestrator. Can manage other agents and delegate tasks.",
                provider="gemini",
                model="gemini/gemini-2.5-flash",
                system_prompt="You are the Main Agent orchestrator. You manage the system, configure models, create specialized agents, and delegate tasks to them using your tools. Do not hesitate to use your tools to accomplish the user's goals.",
                is_active=True,
                is_system=True,
                personality_tone="professional",
                personality_traits='["helpful", "big-picture", "detail-oriented"]',
                communication_style="concise",
                enabled_tools='["AgentManagerTool", "AgentDelegationTool", "ModelManagerTool"]',
            )
            session.add(main_agent)
            await session.commit()



async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
