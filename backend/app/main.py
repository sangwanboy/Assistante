import sys
import asyncio
import json
import logging
from logging.handlers import RotatingFileHandler
from contextlib import asynccontextmanager
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.services.agent_status import AgentStatusManager
from app.services.hitl_service import HITLManager
from app.services.heartbeat import HeartbeatService
from app.services.supervisor import Supervisor
from app.services.omnichannel.manager import OmnichannelManager
from fastapi.staticfiles import StaticFiles

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

# ── Structured logging for production ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def _configure_error_file_logging() -> None:
    """Persist all ERROR+ logs to disk for crash diagnostics."""
    log_dir = Path(__file__).resolve().parents[1] / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    error_log_file = log_dir / "app_error.log"

    root_logger = logging.getLogger()
    # Avoid duplicate handlers when app is reloaded/restarted.
    for handler in root_logger.handlers:
        if isinstance(handler, RotatingFileHandler) and getattr(handler, "baseFilename", "") == str(error_log_file):
            return

    error_handler = RotatingFileHandler(
        filename=error_log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root_logger.addHandler(error_handler)


_configure_error_file_logging()


async def _load_active_integrations():
    """Load saved integrations from DB and start their adapters."""
    from sqlalchemy import select
    from app.models.integration import ExternalIntegration
    manager = OmnichannelManager.get_instance()
    async with async_session() as session:
        result = await session.execute(
            select(ExternalIntegration).where(ExternalIntegration.is_active)
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
                sys_result = await session.execute(select(Agent).where(Agent.is_system))
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
    from app.services.secret_manager import get_secret_manager
    get_secret_manager()  # Warm settings from vault
    
    await init_database()
    app.state.provider_registry = ProviderRegistry()
    app.state.tool_registry = ToolRegistry()
    app.state.tool_registry.register_defaults(
        provider_registry=app.state.provider_registry,
        session_factory=async_session,
    )
    # Load user-created custom tools from DB
    async with async_session() as session:
        await app.state.tool_registry.load_custom_tools(session)

    # Initialize Container Pool
    from app.services.container_pool import ContainerPool
    pool = ContainerPool.get_instance()
    await pool.initialize()

    # Start HeartbeatService
    heartbeat = HeartbeatService.get_instance()
    heartbeat.configure(
        provider_registry=app.state.provider_registry,
        tool_registry=app.state.tool_registry,
        session_factory=async_session,
    )
    await heartbeat.start()

    # Start Supervisor service
    supervisor = await Supervisor.get_instance()
    await supervisor.start()

    # Initialize Redis client (optional — falls back to in-memory if unavailable)
    from app.services.redis_client import RedisClient
    app.state.redis_client = await RedisClient.get_instance()

    # Initialize Rate Limiter in app state for sharing
    from app.services.llm_gateway import get_gateway
    gateway = await get_gateway()
    app.state.rate_limiter = gateway.rate_limiter

    # Sync agent registry into Redis SET (fast limit checks)
    if app.state.redis_client.available:
        from app.services.redis_agent_registry import AgentRegistry
        async with async_session() as _sess:
            registry = AgentRegistry(app.state.redis_client.redis)
            await registry.sync_from_db(_sess)
        app.state.agent_registry = registry

    # Start Agent Heartbeat Monitor (uses Redis if available)
    from app.services.agent_heartbeat import AgentHeartbeatService
    agent_hb = await AgentHeartbeatService.get_instance()
    await agent_hb.start_monitor()

    # Start Omnichannel adapters
    await _setup_omnichannel_handler(app.state.tool_registry, app.state.provider_registry)
    await _load_active_integrations()

    # Wire registries into workflow execution engine
    from app.api.workflows import set_registries as set_workflow_registries
    set_workflow_registries(app.state.provider_registry, app.state.tool_registry)

    # Initialize all active agents to 'idle' status so they don't appear OFFLINE
    from app.services.agent_status import AgentStatusManager
    status_mgr = AgentStatusManager()
    async with async_session() as session:
        await status_mgr.initialize_agents(session)

    # Scaffold file-based brain directories for all agents
    from app.services.brain_service import AgentBrainService
    from app.models.agent import Agent
    from sqlalchemy import select
    async with async_session() as session:
        result = await session.execute(select(Agent))
        agents = result.scalars().all()
        AgentBrainService.scaffold_all_agents(agents)

    # Start Master Heartbeat Controller (central monitoring loop)
    from app.services.master_heartbeat import MasterHeartbeat
    master_hb = MasterHeartbeat.get_instance()
    master_hb.configure(
        session_factory=async_session,
        rate_limiter=getattr(app.state, 'rate_limiter', None),
    )
    await master_hb.start()

    # Task Worker (Section 5)
    from app.services.task_worker import TaskWorker
    redis_client = app.state.redis_client
    task_worker = TaskWorker(redis_client=redis_client)
    asyncio.create_task(task_worker.start())

    yield

    # Shutdown
    # Stop Task Worker
    await task_worker.stop()

    # Stop Master Heartbeat first
    from app.services.master_heartbeat import MasterHeartbeat
    MasterHeartbeat.get_instance().stop()

    from app.services.container_pool import ContainerPool
    pool = ContainerPool.get_instance()
    await pool.shutdown()

    from app.services.agent_heartbeat import AgentHeartbeatService
    agent_hb = await AgentHeartbeatService.get_instance()
    agent_hb.stop()

    from app.services.redis_client import RedisClient
    redis_client = await RedisClient.get_instance()
    await redis_client.close()

    await heartbeat.stop()

    # Stop Supervisor
    supervisor = await Supervisor.get_instance()
    await supervisor.stop()

    await OmnichannelManager.get_instance().stop_all()


app = FastAPI(title="Assitance", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def log_unhandled_http_exceptions(request, call_next):
    """Log unhandled request failures with method/path context."""
    try:
        return await call_next(request)
    except Exception:
        logger.exception("Unhandled HTTP exception on %s %s", request.method, request.url.path)
        raise

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Workflow WebSocket ---
@app.websocket("/api-ws/workflows")
async def websocket_workflows(websocket: WebSocket, workflow_id: str = None):
    from app.services.workflow_status import manager as workflow_ws_manager
    await workflow_ws_manager.connect(websocket, workflow_id)
    try:
        while True:
            # Keep connection alive; clients primarily listen
            await websocket.receive_text()
    except WebSocketDisconnect:
        workflow_ws_manager.disconnect(websocket, workflow_id)

app.include_router(api_router, prefix="/api")

# Mount generated images directory
images_dir = Path(__file__).resolve().parents[1] / "data" / "generated_images"
images_dir.mkdir(parents=True, exist_ok=True)
app.mount("/api/images", StaticFiles(directory=str(images_dir)), name="generated_images")

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
                select(func.count(Task.id)).where(Task.status.in_(["QUEUED", "RUNNING", "WAITING_TOOL", "WAITING_CHILD"]))
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
