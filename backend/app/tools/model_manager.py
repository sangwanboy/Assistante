from typing import Any
import json
from sqlalchemy import select
from app.tools.base import BaseTool
from app.db.engine import async_session
from app.models.model_config import ModelConfig

class ModelManagerTool(BaseTool):
    @property
    def name(self) -> str:
        return "ModelManagerTool"

    @property
    def description(self) -> str:
        return (
            "Creates, reads, updates, or deletes AI Model configurations in the system. "
            "Use this to configure what base models (e.g. gemini-2.5-flash, gpt-4o) are available to agents."
        )

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "What to do: 'list', 'create', 'update', or 'delete'",
                    "enum": ["list", "create", "update", "delete"]
                },
                "id": {
                    "type": "string",
                    "description": "The exact model ID string (e.g. 'gemini-2.5-flash'). Required for all actions except 'list'."
                },
                "provider": {"type": "string", "description": "Provider name: 'gemini', 'openai', 'anthropic', 'ollama'"},
                "name": {"type": "string", "description": "Human-readable name (e.g. 'Gemini 2.5 Flash')"},
                "context_window": {"type": "integer", "description": "Maximum context window (e.g. 1048576)"},
                "is_vision": {"type": "boolean", "description": "True if the model supports images"}
            },
            "required": ["action"]
        }

    async def execute(self, **params: Any) -> str:
        action = params.get("action")
        model_id = params.get("id")
        
        async with async_session() as session:
            if action == "list":
                result = await session.execute(select(ModelConfig))
                models = [
                    {
                        "id": m.id, 
                        "provider": m.provider, 
                        "name": m.name, 
                        "context_window": m.context_window, 
                        "is_vision": m.is_vision
                    } for m in result.scalars().all()
                ]
                return json.dumps(models, indent=2)
                
            if not model_id:
                return "Error: 'id' is required for create, update, or delete."
                
            model = await session.get(ModelConfig, model_id)
            
            if action == "create":
                if model:
                    return f"Error: Model with ID '{model_id}' already exists."
                
                new_model = ModelConfig(
                    id=model_id,
                    provider=params.get("provider", "openai"),
                    name=params.get("name", model_id),
                    context_window=params.get("context_window", 8192),
                    is_vision=params.get("is_vision", False)
                )
                session.add(new_model)
                await session.commit()
                return f"Model '{model_id}' created successfully."
                
            if not model:
                return f"Error: Model with ID '{model_id}' not found."
                
            if action == "delete":
                await session.delete(model)
                await session.commit()
                return f"Model '{model_id}' deleted successfully."
                
            if action == "update":
                if "provider" in params: model.provider = params["provider"]
                if "name" in params: model.name = params["name"]
                if "context_window" in params: model.context_window = params["context_window"]
                if "is_vision" in params: model.is_vision = params["is_vision"]
                
                await session.commit()
                return f"Model '{model_id}' updated successfully."
                
        return "Error: Unknown action."
