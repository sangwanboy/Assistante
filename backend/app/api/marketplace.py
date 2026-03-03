"""REST API for the Skill Marketplace (read-only catalog + install into DB)."""
from typing import List, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.services.marketplace_service import MarketplaceService
from app.models.skill import Skill

router = APIRouter()
_svc = MarketplaceService()


@router.get("", response_model=List[dict])
async def list_marketplace_skills():
    """List all pre-built skills in the marketplace catalog."""
    return _svc.list_skills()


@router.get("/{skill_id}", response_model=dict)
async def get_marketplace_skill(skill_id: str):
    """Get details of a single marketplace skill."""
    skill = _svc.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Marketplace skill not found")
    return skill


@router.post("/{skill_id}/install")
async def install_marketplace_skill(
    skill_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Install a marketplace skill into the user's active skill library."""
    skill_data = _svc.get_skill(skill_id)
    if not skill_data:
        raise HTTPException(status_code=404, detail="Marketplace skill not found")

    # Check if already installed
    from sqlalchemy import select
    existing = await session.execute(
        select(Skill).where(Skill.name == skill_data["name"])
    )
    if existing.scalar_one_or_none():
        return {"ok": True, "message": "Skill already installed", "installed": False}

    skill = Skill(
        name=skill_data["name"],
        description=skill_data["description"],
        instructions=skill_data["instructions"],
        is_active=True,
        user_invocable=True,
        metadata_json=str({"source": "marketplace", "version": skill_data.get("version")}),
    )
    session.add(skill)
    await session.commit()
    await session.refresh(skill)
    return {"ok": True, "message": f"Skill '{skill_data['name']}' installed", "installed": True, "skill_id": skill.id}
