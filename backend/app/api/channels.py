from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.engine import get_session
from app.models.channel import Channel
from app.models.channel_agent import ChannelAgent
from app.models.agent import Agent
from app.schemas.channel import ChannelCreate, ChannelUpdate, ChannelOut, ChannelAgentAdd
from app.schemas.agent import AgentOut

router = APIRouter()

@router.get("", response_model=list[ChannelOut])
async def get_channels(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Channel).order_by(Channel.created_at))
    return list(result.scalars().all())

@router.post("", response_model=ChannelOut)
async def create_channel(channel_data: ChannelCreate, session: AsyncSession = Depends(get_session)):
    channel = Channel(**channel_data.model_dump())
    session.add(channel)
    await session.commit()
    await session.refresh(channel)
    return channel

@router.patch("/{channel_id}", response_model=ChannelOut)
async def update_channel(channel_id: str, channel_data: ChannelUpdate, session: AsyncSession = Depends(get_session)):
    channel = await session.get(Channel, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    update_data = channel_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(channel, key, value)
        
    await session.commit()
    await session.refresh(channel)
    return channel

@router.delete("/{channel_id}")
async def delete_channel(channel_id: str, session: AsyncSession = Depends(get_session)):
    channel = await session.get(Channel, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
        
    if channel.is_announcement:
        raise HTTPException(status_code=403, detail="Cannot delete the Announcements channel")
        
    await session.delete(channel)
    await session.commit()
    return {"status": "ok"}

@router.get("/{channel_id}/agents", response_model=list[AgentOut])
async def get_channel_agents(channel_id: str, session: AsyncSession = Depends(get_session)):
    channel = await session.get(Channel, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
        
    if channel.is_announcement:
        # Announcements has all active agents
        stmt = select(Agent).where(Agent.is_active == True)
    else:
        stmt = select(Agent).join(ChannelAgent).where(ChannelAgent.channel_id == channel_id)
        
    result = await session.execute(stmt)
    return list(result.scalars().all())

@router.post("/{channel_id}/agents")
async def add_agent_to_channel(channel_id: str, data: ChannelAgentAdd, session: AsyncSession = Depends(get_session)):
    channel = await session.get(Channel, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
        
    agent = await session.get(Agent, data.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    # Check if already exists
    stmt = select(ChannelAgent).where(
        ChannelAgent.channel_id == channel_id, 
        ChannelAgent.agent_id == data.agent_id
    )
    existing = await session.scalar(stmt)
    if not existing:
        link = ChannelAgent(channel_id=channel_id, agent_id=data.agent_id)
        session.add(link)
        await session.commit()
        
    return {"status": "ok"}

@router.delete("/{channel_id}/agents/{agent_id}")
async def remove_agent_from_channel(channel_id: str, agent_id: str, session: AsyncSession = Depends(get_session)):
    stmt = select(ChannelAgent).where(
        ChannelAgent.channel_id == channel_id, 
        ChannelAgent.agent_id == agent_id
    )
    link = await session.scalar(stmt)
    if link:
        await session.delete(link)
        await session.commit()
        
    return {"status": "ok"}
