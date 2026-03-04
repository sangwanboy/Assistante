from fastapi import APIRouter

from app.api.chat import router as chat_router
from app.api.conversations import router as conversations_router
from app.api.models_api import router as models_router
from app.api.tools_api import router as tools_router
from app.api.settings_api import router as settings_router
from app.api.agents import router as agents_router
from app.api.knowledge import router as knowledge_router
from app.api.workflows import router as workflows_router
from app.api.custom_tools import router as custom_tools_router
from app.api.skills import router as skills_router
from app.api.channels import router as channels_router
from app.api.audio import router as audio_router
from app.api.integrations import router as integrations_router
from app.api.schedules import router as schedules_router
from app.api.marketplace import router as marketplace_router
from app.api.agent_messaging import router as agent_messaging_router
from app.api.tasks import router as tasks_router
from app.api.chains import router as chains_router

api_router = APIRouter()

api_router.include_router(chat_router, tags=["Chat"])
api_router.include_router(conversations_router, prefix="/conversations", tags=["Conversations"])
api_router.include_router(models_router, prefix="/models", tags=["Models"])
api_router.include_router(tools_router, prefix="/tools", tags=["Tools"])
api_router.include_router(settings_router, prefix="/settings", tags=["Settings"])
api_router.include_router(agents_router, prefix="/agents", tags=["Agents"])
api_router.include_router(knowledge_router, prefix="/knowledge", tags=["Knowledge Base"])
api_router.include_router(workflows_router, prefix="/workflows", tags=["Workflows"])
api_router.include_router(custom_tools_router, prefix="/custom-tools", tags=["Custom Tools"])
api_router.include_router(skills_router, prefix="/skills", tags=["Skills"])
api_router.include_router(channels_router, prefix="/channels", tags=["Channels"])
api_router.include_router(audio_router, prefix="/audio", tags=["Audio"])
api_router.include_router(integrations_router, prefix="/integrations", tags=["Omnichannel"])
api_router.include_router(schedules_router, prefix="/schedules", tags=["Heartbeat"])
api_router.include_router(marketplace_router, prefix="/marketplace", tags=["Marketplace"])
api_router.include_router(agent_messaging_router, prefix="/messaging", tags=["Agent Messaging"])
api_router.include_router(tasks_router, prefix="/tasks", tags=["Tasks"])
api_router.include_router(chains_router, prefix="/chains", tags=["Delegation Chains"])
