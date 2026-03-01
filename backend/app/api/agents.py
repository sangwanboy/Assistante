from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from pydantic import BaseModel

from app.db.engine import get_session
from app.models.agent import Agent
from app.schemas.agent import AgentCreate, AgentUpdate, AgentOut

router = APIRouter()


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
    result = await db.execute(select(Agent).order_by(Agent.name))
    return result.scalars().all()


@router.post("", response_model=AgentOut, status_code=status.HTTP_201_CREATED)
async def create_agent(agent_in: AgentCreate, db: AsyncSession = Depends(get_session)):
    agent = Agent(**agent_in.model_dump())
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
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

    update_data = agent_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(agent, key, value)

    await db.commit()
    await db.refresh(agent)
    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(agent_id: str, db: AsyncSession = Depends(get_session)):
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    if getattr(agent, "is_system", False):
        raise HTTPException(status_code=403, detail="Cannot delete a system orchestrator agent")

    await db.delete(agent)
    await db.commit()
    return None


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
        raise HTTPException(status_code=500, detail=f"Agent chat error: {str(e)}")

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
