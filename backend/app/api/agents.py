from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List, Optional
from pydantic import BaseModel
import logging

from app.db.engine import get_session
from app.models.agent import Agent
from app.models.conversation import Conversation
from app.schemas.agent import AgentCreate, AgentUpdate, AgentOut

router = APIRouter()
logger = logging.getLogger(__name__)


DEPRECATED_GEMINI_MODELS = {
    "gemini-3.1-flash-preview",
    "gemini-3.1-flash-lite-preview",
}


def _validate_agent_model(provider: str | None, model: str | None) -> None:
    if not provider or not model:
        return

    p = provider.strip().lower()
    m = model.strip()
    model_id = m.split("/", 1)[1] if "/" in m else m

    if p == "gemini" and model_id in DEPRECATED_GEMINI_MODELS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Model '{model_id}' is deprecated and blocked. "
                "Use an available Gemini model such as gemini/gemini-2.5-flash, gemini/gemini-2.5-flash-lite, gemini/gemini-2.5-pro, or verified preview IDs."
            ),
        )


class GeneratePersonalityRequest(BaseModel):
    name: str
    description: str = ""
    model: str = ""  # provider/model string


@router.post("/generate-personality")
async def generate_personality(
    req: GeneratePersonalityRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    """Use the LLM to auto-generate personality for an agent based on name and description."""
    import json as _json

    model_string = req.model or "gemini/gemini-2.5-flash"
    provider_name = model_string.split("/", 1)[0] if "/" in model_string else "gemini"
    model_id = model_string.split("/", 1)[1] if "/" in model_string else model_string

    provider = request.app.state.provider_registry.get(provider_name)
    if not provider:
        raise HTTPException(status_code=400, detail=f"Provider '{provider_name}' not available")

    prompt = f"""Based on this AI agent's name and description, generate a fitting personality profile.

Agent Name: {req.name}
Agent Description: {req.description or 'Not provided'}

Return ONLY valid JSON with these fields:
{{
  "personality_tone": "one of: professional, friendly, sarcastic, empathetic, witty, serious, playful",
  "personality_traits": ["list of 3-5 traits from: curious, concise, creative, helpful, critical, patient, humorous, detail-oriented, big-picture, cautious"],
  "communication_style": "one of: formal, casual, technical, storytelling, concise, verbose",
  "reasoning_style": "one of: analytical, creative, balanced, step-by-step, intuitive",
  "system_prompt": "A 2-3 sentence system prompt that defines this agent's role and behavior"
}}"""

    from app.providers.base import ChatMessage
    messages = [ChatMessage(role="user", content=prompt)]

    try:
        full = ""
        async for chunk in provider.stream(messages, model_id, temperature=0.7):
            if chunk.delta:
                full += chunk.delta

        # Extract JSON from response
        start = full.find("{")
        end = full.rfind("}") + 1
        if start >= 0 and end > start:
            result = _json.loads(full[start:end])
            # Ensure traits is a JSON string
            if isinstance(result.get("personality_traits"), list):
                result["personality_traits"] = _json.dumps(result["personality_traits"])
            return result
        else:
            raise HTTPException(status_code=500, detail="LLM did not return valid JSON")
    except _json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse LLM response as JSON")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation error: {str(e)}")


@router.get("", response_model=List[AgentOut])
async def list_agents(db: AsyncSession = Depends(get_session)):
    result = await db.execute(
        select(Agent).where(Agent.status != "deleted").order_by(Agent.name)
    )
    return result.scalars().all()


@router.get("/discover", response_model=List[AgentOut])
async def discover_agents(
    role: Optional[str] = Query(None, description="Filter by role (partial match)"),
    tools: Optional[str] = Query(None, description="Filter by tool name in enabled_tools"),
    group: Optional[str] = Query(None, description="Filter by group membership"),
    capability: Optional[str] = Query(None, description="General search across role, description, tools"),
    db: AsyncSession = Depends(get_session),
):
    """Discover agents by role, tools, group membership, or general capability."""
    import json as _json

    stmt = select(Agent).where(Agent.is_active == True, Agent.status != "deleted")  # noqa: E712
    filters = []

    if role:
        filters.append(Agent.role.ilike(f"%{role}%"))
    if tools:
        filters.append(Agent.enabled_tools.ilike(f"%{tools}%"))
    if group:
        filters.append(Agent.groups.ilike(f"%{group}%"))
    if capability:
        filters.append(or_(
            Agent.role.ilike(f"%{capability}%"),
            Agent.description.ilike(f"%{capability}%"),
            Agent.enabled_tools.ilike(f"%{capability}%"),
            Agent.name.ilike(f"%{capability}%"),
        ))

    if filters:
        from sqlalchemy import and_
        stmt = stmt.where(and_(*filters))

    stmt = stmt.order_by(Agent.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=AgentOut, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_in: AgentCreate,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    from app.services.agent_limits import can_create_agent

    rc_wrapper = getattr(request.app.state, "redis_client", None)
    redis = rc_wrapper.redis if rc_wrapper is not None else None

    allowed, reason = await can_create_agent(db, redis)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=reason,
        )

    payload = agent_in.model_dump()
    _validate_agent_model(payload.get("provider"), payload.get("model"))
    agent = Agent(**payload)
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    # Register in Redis agent registry (key: agents:active, type: SET)
    if redis is not None:
        try:
            await redis.sadd("agents:active", agent.id)
        except Exception:
            pass

    return agent


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_session)):
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.put("/{agent_id}", response_model=AgentOut)
async def update_agent(agent_id: str, agent_in: AgentUpdate, db: AsyncSession = Depends(get_session)):
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    old_model = agent.model
    old_provider = agent.provider
    update_data = agent_in.model_dump(exclude_unset=True)
    effective_provider = update_data.get("provider", agent.provider)
    effective_model = update_data.get("model", agent.model)
    _validate_agent_model(effective_provider, effective_model)

    for key, value in update_data.items():
        setattr(agent, key, value)

    # Keep agent-linked conversations aligned with agent runtime model.
    # This prevents stale "active context model" and websocket payload drift.
    model_changed = "model" in update_data or "provider" in update_data
    synced_conversations = 0
    if model_changed:
        stmt = select(Conversation).where(Conversation.agent_id == agent_id)
        rows = await db.execute(stmt)
        convs = rows.scalars().all()
        for conv in convs:
            conv.model = agent.model
            synced_conversations += 1

        logger.info(
            "Agent %s model update: %s/%s -> %s/%s (synced_conversations=%s)",
            agent_id,
            old_provider,
            old_model,
            agent.provider,
            agent.model,
            synced_conversations,
        )

    await db.commit()
    await db.refresh(agent)
    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: str,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if getattr(agent, "is_system", False):
        raise HTTPException(status_code=403, detail="Cannot delete a system orchestrator agent")

    # Soft-delete: mark status='deleted' so capacity is freed, row retained for audit.
    agent.status = "deleted"
    agent.is_active = False
    await db.commit()

    # Free capacity in Redis registry
    rc_wrapper = getattr(request.app.state, "redis_client", None)
    redis = rc_wrapper.redis if rc_wrapper is not None else None
    if redis is not None:
        try:
            await redis.srem("agents:active", agent_id)
        except Exception:
            pass

    return None


class AgentEvolveRequest(BaseModel):
    memory_update: Optional[str] = None
    tool_strategy: Optional[str] = None
    execution_pattern: Optional[str] = None


@router.post("/{agent_id}/evolve")
async def evolve_agent(
    agent_id: str,
    req: AgentEvolveRequest,
    db: AsyncSession = Depends(get_session),
):
    """Allow an agent to evolve by accumulating memory and strategies after tasks.
    
    Unlike update, this APPENDS to memory_context rather than overwriting.
    Sets the agent to 'learning' state during the process.
    """
    from app.services.agent_status import AgentStatusManager, AgentState

    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Set learning state
    status_mgr = await AgentStatusManager.get_instance()
    status_mgr.set_status(agent_id, AgentState.LEARNING, "Evolving from task experience")

    updated_fields = []

    if req.memory_update:
        existing = agent.memory_context or ""
        separator = "\n---\n" if existing else ""
        agent.memory_context = existing + separator + req.memory_update
        updated_fields.append("memory_context")

    if req.tool_strategy:
        existing_instructions = agent.memory_instructions or ""
        separator = "\n" if existing_instructions else ""
        agent.memory_instructions = existing_instructions + separator + f"[Strategy] {req.tool_strategy}"
        updated_fields.append("memory_instructions")

    if req.execution_pattern:
        existing_instructions = agent.memory_instructions or ""
        separator = "\n" if existing_instructions else ""
        agent.memory_instructions = existing_instructions + separator + f"[Pattern] {req.execution_pattern}"
        updated_fields.append("memory_instructions")

    await db.commit()
    await db.refresh(agent)

    # Return to idle
    status_mgr.set_status(agent_id, AgentState.IDLE)

    return {
        "status": "evolved",
        "agent_id": agent_id,
        "agent_name": agent.name,
        "updated_fields": updated_fields,
    }


# ──────────────────────────────────────────────
# Agent-to-Agent Chat endpoint
# Allows one agent to send a message to another agent and get a response
# ──────────────────────────────────────────────

class AgentChatRequest(BaseModel):
    message: str
    target_agent_id: str
    conversation_id: str = ""  # Optional: persist into an existing conversation
    temperature: float = 0.7


class AgentChatResponse(BaseModel):
    response: str
    from_agent_id: str
    from_agent_name: str
    to_agent_id: str
    to_agent_name: str
    conversation_id: str


@router.post("/{agent_id}/chat", response_model=AgentChatResponse)
async def agent_to_agent_chat(
    agent_id: str,
    req: AgentChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    """
    Send a message FROM agent `agent_id` TO agent `target_agent_id`.
    The source agent's name is prepended to the message so the target
    agent has conversational context.  The response is returned as JSON
    (non-streaming) so that orchestrators can chain calls programmatically.
    """
    # Load both agents
    from_agent = await db.get(Agent, agent_id)
    if not from_agent:
        raise HTTPException(status_code=404, detail=f"Source agent '{agent_id}' not found")

    to_agent = await db.get(Agent, req.target_agent_id)
    if not to_agent:
        raise HTTPException(status_code=404, detail=f"Target agent '{req.target_agent_id}' not found")

    # Compose the message with sender attribution
    attributed_message = f"{from_agent.name}: {req.message}"

    # Use ChatService to run the non-streaming completion scoped to the target agent
    from app.services.chat_service import ChatService
    service = ChatService(
        provider_registry=request.app.state.provider_registry,
        tool_registry=request.app.state.tool_registry,
        session=db,
    )

    try:
        response_text = await service.chat(
            conversation_id=req.conversation_id,
            user_message=attributed_message,
            model_string=to_agent.model,
            system_prompt=to_agent.system_prompt,
            temperature=req.temperature,
        )
    except Exception as e:
        msg = str(e)
        lowered = msg.lower()
        if "quota" in lowered or "resource_exhausted" in lowered or "rate limit" in lowered or "429" in lowered:
            raise HTTPException(status_code=429, detail=f"Agent chat error: {msg}")
            if "api key not valid" in lowered or "api_key_invalid" in lowered or "invalid api key" in lowered:
                raise HTTPException(status_code=401, detail=msg)
            if (
                "provider" in lowered and "not configured" in lowered
            ) or "no available fallback provider" in lowered or "all connection attempts failed" in lowered:
                raise HTTPException(status_code=503, detail=msg)
        raise HTTPException(status_code=500, detail=f"Agent chat error: {msg}")

    # Determine the conversation_id that was used/created
    # chat() creates one if empty; we need to retrieve it from the conversation service
    from app.services.conversation_service import ConversationService
    conv_service = ConversationService(db)
    convs = await conv_service.list_all(limit=1)
    used_conv_id = convs[0].id if convs else req.conversation_id

    return AgentChatResponse(
        response=response_text,
        from_agent_id=from_agent.id,
        from_agent_name=from_agent.name,
        to_agent_id=to_agent.id,
        to_agent_name=to_agent.name,
        conversation_id=used_conv_id,
    )
