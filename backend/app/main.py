from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
import app.models.document  # Ensure model is registered before init_database
import app.models.workflow
from app.db.engine import init_database
from app.providers.registry import ProviderRegistry
from app.tools.registry import ToolRegistry
from app.api.router import api_router
from app.api.chat import websocket_chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_database()
    app.state.provider_registry = ProviderRegistry(settings)
    app.state.tool_registry = ToolRegistry()
    app.state.tool_registry.register_defaults()
    yield
    # Shutdown


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


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
