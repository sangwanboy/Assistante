from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.model_config import ModelConfig
from app.models.model_registry import ModelCapability
from app.config import settings

class ModelRegistryService:
    @staticmethod
    async def get_effective_capabilities(model_id: str, db: AsyncSession) -> dict:
        """
        Resolves capabilities for a model (provider/model_id).
        Precedence: DB (ModelCapability) > App Defaults (ModelConfig) > Settings.
        """
        # 1. Try to find        # Try primary key first, then model_name
        stmt = select(ModelCapability).where(
            (ModelCapability.id == model_id) | (ModelCapability.model_name == model_id)
        ).limit(1)
        result = await db.execute(stmt)
        cap = result.scalar_one_or_none()
        
        provider = "unknown"
        model_name = model_id
        if '/' in model_id:
            provider, model_name = model_id.split('/', 1)

        # 2. Try to find in ModelConfig for context window defaults
        stmt_conf = select(ModelConfig).where(ModelConfig.id == model_name, ModelConfig.provider == provider)
        result_conf = await db.execute(stmt_conf)
        conf = result_conf.scalar_one_or_none()

        # Build defaults
        default_context = conf.context_window if conf else 8192
        default_rpm = 100
        default_tpm = 1000000
        default_rpd = 10000

        # Gemini specific settings fallbacks
        if provider == "gemini":
            default_context = settings.gemini_context_window or 128000
            default_rpm = settings.gemini_rpm or 12
            default_tpm = settings.gemini_tpm or 250000
            default_rpd = settings.gemini_rpd or 1500

        # Combine with precedence
        return {
            "rpm": cap.rpm if cap and cap.rpm is not None else default_rpm,
            "tpm": cap.tpm if cap and cap.tpm is not None else default_tpm,
            "rpd": cap.rpd if cap and cap.rpd is not None else default_rpd,
            "context_window": cap.context_window if cap and cap.context_window is not None else default_context,
            "max_concurrent": cap.max_concurrent_requests if cap else 10,
            "canonical_id": cap.id if cap else model_id,
        }
