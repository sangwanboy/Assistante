"""API routes for delegation chain monitoring."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.models.chain import DelegationChain
from app.schemas.task import ChainOut

router = APIRouter()


@router.get("/active", response_model=list[ChainOut])
async def get_active_chains(session: AsyncSession = Depends(get_session)):
    """List all active delegation chains."""
    stmt = (
        select(DelegationChain)
        .where(DelegationChain.state == "active")
        .order_by(DelegationChain.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/{chain_id}", response_model=ChainOut)
async def get_chain(chain_id: str, session: AsyncSession = Depends(get_session)):
    """Get delegation chain detail."""
    chain = await session.get(DelegationChain, chain_id)
    if not chain:
        raise HTTPException(status_code=404, detail="Chain not found")
    return chain
