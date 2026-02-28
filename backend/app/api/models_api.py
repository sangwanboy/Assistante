from fastapi import APIRouter, Request

from app.schemas.models import ModelInfoOut

router = APIRouter()


@router.get("", response_model=list[ModelInfoOut])
async def list_models(request: Request):
    registry = request.app.state.provider_registry
    models = await registry.all_models()
    return [
        ModelInfoOut(
            id=f"{m.provider}/{m.id}",
            name=m.name,
            provider=m.provider,
            supports_streaming=m.supports_streaming,
            supports_tools=m.supports_tools,
            context_window=m.context_window,
        )
        for m in models
    ]
