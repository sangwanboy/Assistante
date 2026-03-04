import sys
import asyncio
import json
import logging
from contextlib import asynccontextmanager

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.services.agent_status import AgentStatusManager
from app.services.hitl_service import HITLManager
from app.services.heartbeat import HeartbeatService
from app.services.omnichannel.manager import OmnichannelManager

from app.config import settings
import app.models.document  # Ensure model is registered before init_database
import app.models.workflow
import app.models.custom_tool
import app.models.skill
from app.db.engine import init_database, async_session
from app.providers.registry import ProviderRegistry
from app.tools.registry import ToolRegistry
from app.api.router import api_router
from app.api.chat import websocket_chat

logger = logging.getLogger(__name__)


async def _load_active_integrations():
    """Load saved integrations from DB and start their adapters."""
    from sqlalchemy import select
    from app.models.integration import ExternalIntegration
    manager = OmnichannelManager.get_instance()
    async with async_session() as session:
        result = await session.execute(
            select(ExternalIntegration).where(ExternalIntegration.is_active == True)
        )
        integrations = result.scalars().all()
    for integration in integrations:
        try:
            config = json.loads(integration.config_json or "{}")
            await manager.start_adapter(integration.id, integration.platform, config)
        except Exception as exc:
            logger.warning("Failed to start adapter for integration %s: %s", integration.id, exc)


async def _setup_omnichannel_handler(tool_registry: ToolRegistry, provider_registry: ProviderRegistry):
    """Set the incoming message handler for all omnichannel adapters."""
    from app.models.agent import Agent
    from app.models.conversation import Conversation
    from app.services.chat_service import ChatService
    from sqlalchemy import select
    import uuid

    async def handle_incoming(msg):
        async with async_session() as session:
            from app.models.integration import ExternalIntegration
            result = await session.execute(
                select(ExternalIntegration).where(ExternalIntegration.id == msg.integration_id)
            )
            integration = result.scalar_one_or_none()
            agent_id = integration.agent_id if integration else None
            if not agent_id:
                sys_result = await session.execute(select(Agent).where(Agent.is_system == True))
                sys_agent = sys_result.scalar_one_or_none()
                agent_id = sys_agent.id if sys_agent else None
            if not agent_id:
                logger.warning("No agent for omnichannel message; dropping")
                return
            title = f"__omni_{msg.platform}_{msg.external_chat_id}__"
            conv_result = await session.execute(
                select(Conversation).where(Conversation.title == title)
            )
            conv = conv_result.scalar_one_or_none()
            if conv is None:
                agent_result = await session.execute(select(Agent).where(Agent.id == agent_id))
                agent = agent_result.scalar_one_or_none()
                conv = Conversation(
                    id=str(uuid.uuid4()),
                    title=title,
                    agent_id=agent_id,
                    model=(agent.model if agent else "gemini/gemini-2.5-flash"),
                )
                session.add(conv)
                await session.commit()
                await session.refresh(conv)
            chat_svc = ChatService(
                provider_registry=provider_registry,
                tool_registry=tool_registry,
                session=session,
            )
            try:
                response = await chat_svc.chat(
                    conversation_id=conv.id,
                    user_message=f"[{msg.username}]: {msg.text}",
                    model=conv.model,
                )
                omni = OmnichannelManager.get_instance()
                await omni.send(msg.integration_id, msg.external_chat_id, response)
            except Exception as exc:
                logger.error("Omnichannel message failed: %s", exc, exc_info=True)

    OmnichannelManager.get_instance().set_message_handler(handle_incoming)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_database()
    app.state.provider_registry = ProviderRegistry(settings)
    app.state.tool_registry = ToolRegistry()
    app.state.tool_registry.register_defaults(
        provider_registry=app.state.provider_registry,
        session_factory=async_session,
    )
    # Load user-created custom tools from DB
    async with async_session() as session:
        await app.state.tool_registry.load_custom_tools(session)

    # Start HeartbeatService
    heartbeat = HeartbeatService.get_instance()
    heartbeat.configure(
        provider_registry=app.state.provider_registry,
        tool_registry=app.state.tool_registry,
        session_factory=async_session,
    )
    await heartbeat.start()

    # Initialize Redis client (optional — falls back to in-memory if unavailable)
    from app.services.redis_client import RedisClient
    app.state.redis_client = await RedisClient.get_instance()

    # Start Agent Heartbeat Monitor (uses Redis if available)
    from app.services.agent_heartbeat import AgentHeartbeatService
    agent_hb = await AgentHeartbeatService.get_instance()
    await agent_hb.start_monitor()

    # Start Omnichannel adapters
    await _setup_omnichannel_handler(app.state.tool_registry, app.state.provider_registry)
    await _load_active_integrations()

    yield

    # Shutdown
    from app.services.agent_heartbeat import AgentHeartbeatService
    agent_hb = await AgentHeartbeatService.get_instance()
    agent_hb.stop()

    from app.services.redis_client import RedisClient
    redis_client = await RedisClient.get_instance()
    await redis_client.close()

    await heartbeat.stop()
    await OmnichannelManager.get_instance().stop_all()


app = FastAPI(title="Assitance", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

# Mount WebSocket at root (not under /api) so frontend can connect to /ws/chat/{id}
app.websocket("/ws/chat/{conversation_id}")(websocket_chat)


@app.websocket("/api-ws/agents/status")
async def websocket_agents_status(websocket: WebSocket):
    await websocket.accept()
    manager = await AgentStatusManager.get_instance()

    # Send initial state
    await websocket.send_text(json.dumps({
        "type": "initial_status",
        "statuses": manager.get_all_statuses()
    }))

    queue = manager.subscribe()
    try:
        while True:
            message = await queue.get()
            await websocket.send_text(message)
    except WebSocketDisconnect:
        manager.unsubscribe(queue)
    except Exception:
        manager.unsubscribe(queue)


@app.websocket("/api-ws/agents/control")
async def websocket_agents_control(websocket: WebSocket):
    manager = HITLManager.get_instance()
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("action") in ["APPROVE", "DENY"]:
                    manager.resolve_approval(msg.get("task_id"), msg.get("action"))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


@app.get("/api/health")
async def health_check():
    from app.services.agent_status import AgentStatusManager
    status_mgr = await AgentStatusManager.get_instance()
    all_statuses = status_mgr.get_all_statuses()

    from app.models.task import Task
    from app.models.chain import DelegationChain
    from sqlalchemy import select, func

    active_tasks = 0
    active_chains = 0
    try:
        async with async_session() as session:
            active_tasks = await session.scalar(
                select(func.count(Task.id)).where(Task.status.in_(["pending", "running"]))
            ) or 0
            active_chains = await session.scalar(
                select(func.count(DelegationChain.id)).where(DelegationChain.state == "active")
            ) or 0
    except Exception:
        pass

    from app.services.redis_client import RedisClient
    rc = await RedisClient.get_instance()

    return {
        "status": "ok",
        "version": "0.2.0",
        "redis_available": rc.available,
        "agents": all_statuses,
        "active_tasks": active_tasks,
        "active_chains": active_chains,
    }
