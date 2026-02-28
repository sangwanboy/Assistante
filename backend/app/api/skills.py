from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.schemas.skill import (
    SkillCreate,
    SkillUpdate,
    SkillOut,
    SkillImportRequest,
    SkillExportResponse,
)
from app.services.skill_service import SkillService, export_skill_md

router = APIRouter()


@router.get("", response_model=list[SkillOut])
async def list_skills(session: AsyncSession = Depends(get_session)):
    svc = SkillService(session)
    return await svc.list_all()


@router.post("", response_model=SkillOut, status_code=201)
async def create_skill(data: SkillCreate, session: AsyncSession = Depends(get_session)):
    svc = SkillService(session)
    return await svc.create(**data.model_dump())


@router.get("/{skill_id}", response_model=SkillOut)
async def get_skill(skill_id: str, session: AsyncSession = Depends(get_session)):
    svc = SkillService(session)
    skill = await svc.get(skill_id)
    if not skill:
        raise HTTPException(404, "Skill not found")
    return skill


@router.put("/{skill_id}", response_model=SkillOut)
async def update_skill(skill_id: str, data: SkillUpdate, session: AsyncSession = Depends(get_session)):
    svc = SkillService(session)
    skill = await svc.update(skill_id, **data.model_dump(exclude_unset=True))
    if not skill:
        raise HTTPException(404, "Skill not found")
    return skill


@router.delete("/{skill_id}")
async def delete_skill(skill_id: str, session: AsyncSession = Depends(get_session)):
    svc = SkillService(session)
    deleted = await svc.delete(skill_id)
    if not deleted:
        raise HTTPException(404, "Skill not found")
    return {"status": "deleted"}


@router.post("/import", response_model=SkillOut, status_code=201)
async def import_skill(data: SkillImportRequest, session: AsyncSession = Depends(get_session)):
    """Import a skill from raw SKILL.md content (OpenClaw format)."""
    svc = SkillService(session)
    return await svc.import_from_content(data.content)


@router.get("/{skill_id}/export", response_model=SkillExportResponse)
async def export_skill(skill_id: str, session: AsyncSession = Depends(get_session)):
    """Export a skill as OpenClaw-format SKILL.md content."""
    svc = SkillService(session)
    skill = await svc.get(skill_id)
    if not skill:
        raise HTTPException(404, "Skill not found")
    content = export_skill_md(skill)
    filename = f"{skill.name.lower().replace(' ', '_')}_SKILL.md"
    return SkillExportResponse(filename=filename, content=content)
