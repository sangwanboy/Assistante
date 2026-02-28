from fastapi import APIRouter

from app.api.chat import router as chat_router
from app.api.conversations import router as conversations_router
from app.api.models_api import router as models_router
from app.api.tools_api import router as tools_router
from app.api.settings_api import router as settings_router
from app.api.agents import router as agents_router
from app.api.knowledge import router as knowledge_router
from app.api.workflows import router as workflows_router

api_router = APIRouter()

api_router.include_router(chat_router, tags=["Chat"])
api_router.include_router(conversations_router, prefix="/conversations", tags=["Conversations"])
api_router.include_router(models_router, prefix="/models", tags=["Models"])
api_router.include_router(tools_router, prefix="/tools", tags=["Tools"])
api_router.include_router(settings_router, prefix="/settings", tags=["Settings"])
api_router.include_router(agents_router, prefix="/agents", tags=["Agents"])
api_router.include_router(knowledge_router, prefix="/knowledge", tags=["Knowledge Base"])
api_router.include_router(workflows_router, prefix="/workflows", tags=["Workflows"])
