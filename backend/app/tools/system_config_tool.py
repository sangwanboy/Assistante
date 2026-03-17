from typing import Any
import json
from app.tools.base import BaseTool
from app.services.secret_manager import get_secret_manager

class SystemConfigTool(BaseTool):
    @property
    def name(self) -> str:
        return "SystemConfigTool"

    @property
    def description(self) -> str:
        return (
            "Allows managing system-wide configuration and secrets (e.g. API keys for search, vision, etc.). "
            "Use this to save or update API keys provided by the user for global tools like Brave Search."
        )

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "What to do: 'set_secret' or 'has_secret'",
                    "enum": ["set_secret", "has_secret"]
                },
                "key": {
                    "type": "string",
                    "description": "The name of the secret/config key (e.g. 'brave_search', 'openai', 'anthropic')"
                },
                "value": {
                    "type": "string",
                    "description": "The value to set (only for 'set_secret'). If empty, removes the secret."
                }
            },
            "required": ["action", "key"]
        }

    async def execute(self, **params: Any) -> str:
        action = params.get("action")
        key = params.get("key")
        value = params.get("value")
        
        sm = get_secret_manager()
        
        if action == "has_secret":
            exists = sm.has_api_key(key)
            return f"Configuration for '{key}' exists: {exists}"
            
        if action == "set_secret":
            sm.set_api_key(key, value)
            if value:
                return f"Successfully updated system configuration for '{key}'."
            else:
                return f"Successfully removed system configuration for '{key}'."
                
        return "Error: Unknown action."
