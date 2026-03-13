from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.engine import get_session
from app.models.model_config import ModelConfig
from app.models.model_registry import ModelCapability
from app.schemas.models import ModelInfoOut, ModelCapabilityUpdate

router = APIRouter()

@router.get("", response_model=list[ModelInfoOut])
async def list_models(db: AsyncSession = Depends(get_session)):
    try:
        from app.services.model_registry_service import ModelRegistryService
        stmt = select(ModelConfig).where(ModelConfig.is_active)
        result = await db.execute(stmt)
        configs = result.scalars().all()
        
        models_out = []
        for m in configs:
            model_id = f"{m.provider}/{m.id}"
            caps = await ModelRegistryService.get_effective_capabilities(model_id, db)
            
            models_out.append(ModelInfoOut(
                id=model_id,
                name=m.name,
                provider=m.provider,
                supports_streaming=True,
                supports_tools=True,
                context_window=caps["context_window"],
                rpm=caps["rpm"],
                tpm=caps["tpm"],
                rpd=caps["rpd"],
                is_fallback=caps.get("is_fallback", False)
            ))
        return models_out
    except Exception as e:
        print(f"ERROR IN MODELS API: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

@router.put("/{model_id:path}/capability")
async def update_model_capability(
    model_id: str,
    update: ModelCapabilityUpdate,
    db: AsyncSession = Depends(get_session)
):
    try:
        # Check if ModelCapability exists
        stmt = select(ModelCapability).where(ModelCapability.id == model_id)
        result = await db.execute(stmt)
        cap = result.scalar_one_or_none()
        
        if not cap:
            # If it doesn't exist, we need to create it.
            # We assume the model exists in ModelConfig if we're hitting this.
            if '/' not in model_id:
                # Fallback if id is just the name (legacy)
                provider = "unknown"
                name = model_id
            else:
                provider, name = model_id.split('/', 1)
            cap = ModelCapability(id=model_id, provider=provider, model_name=name)
            db.add(cap)
        
        # Update fields if provided in the request (including nulls)
        update_data = update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(cap, field):
                setattr(cap, field, value)
            
        await db.commit()
        return {"status": "ok", "id": model_id}
    except Exception as e:
        print(f"ERROR UPDATING MODEL CAPABILITY: {str(e)}")
        await db.rollback()
        raise
