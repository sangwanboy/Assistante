import os
import logging

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import settings
from app.db.base import Base

logger = logging.getLogger(__name__)

# ── Engine Configuration ──
_engine_kwargs: dict = {"echo": False}

if settings.is_sqlite:
    # SQLite: local file-based, no pooling needed
    DATABASE_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "data",
        "assitance.db",
    )
    DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"
else:
    # PostgreSQL: connection pooling enabled
    DATABASE_URL = settings.database_url
    _engine_kwargs.update(
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

engine = create_async_engine(DATABASE_URL, **_engine_kwargs)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_database():
    """Initialize database: create tables and seed defaults."""
    if settings.is_sqlite:
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

    # Import all models so metadata is populated
    import app.models  # noqa: F401
    import app.models.model_config  # noqa: F401
    import app.models.agent_memory  # noqa: F401
    import app.models.announcement  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables created/verified (%s)", "SQLite" if settings.is_sqlite else "PostgreSQL")

    # Seed defaults
    await _seed_defaults()


async def _seed_defaults():
    """Seed default model configs, channels, and system agent."""
    from app.models.model_config import ModelConfig
    from app.models.agent import Agent, new_id
    from app.models.channel import Channel
    from app.models.model_registry import ModelCapability

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

        # Seed ModelCapability registry entries
        stmt = select(func.count(ModelCapability.id))
        cap_count = await session.scalar(stmt)
        if cap_count == 0:
            default_capabilities = [
                ModelCapability(id="gemini/gemini-2.5-flash", provider="gemini", model_name="gemini-2.5-flash", rpm=1000, tpm=4000000, rpd=50000, context_window=1048576),
                ModelCapability(id="gemini/gemini-2.5-pro", provider="gemini", model_name="gemini-2.5-pro", rpm=150, tpm=2000000, rpd=10000, context_window=2097152),
                ModelCapability(id="anthropic/claude-3-5-sonnet-20241022", provider="anthropic", model_name="claude-3-5-sonnet-20241022", rpm=50, tpm=100000, rpd=5000, context_window=200000),
                ModelCapability(id="openai/gpt-4o", provider="openai", model_name="gpt-4o", rpm=500, tpm=800000, rpd=10000, context_window=128000),
            ]
            session.add_all(default_capabilities)
            await session.commit()

        # Seed Announcements Channel
        stmt = select(func.count(Channel.id)).where(Channel.is_announcement)
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
        stmt = select(func.count(Agent.id)).where(Agent.is_system)
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
                capabilities='["orchestration", "task_delegation", "agent_management", "model_management"]',
                performance_metrics='{"success_rate": 1.0, "tasks_completed": 0, "tasks_failed": 0, "avg_completion_time": 0}',
            )
            session.add(main_agent)
            await session.commit()

    logger.info("Database seeding complete")


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
