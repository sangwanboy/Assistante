from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.engine import get_session
from app.models.model_config import ModelConfig
from app.schemas.models import ModelInfoOut

router = APIRouter()

@router.get("", response_model=list[ModelInfoOut])
async def list_models(db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(ModelConfig).where(ModelConfig.is_active == True))
    models = result.scalars().all()
    
    return [
        ModelInfoOut(
            id=f"{m.provider}/{m.id}",
            name=m.name,
            provider=m.provider,
            supports_streaming=True,  # Defaulting true for known providers
            supports_tools=True,
            context_window=m.context_window,
        )
        for m in models
    ]
