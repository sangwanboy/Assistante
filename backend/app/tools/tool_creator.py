import json

from app.tools.base import BaseTool


def _get_registry():
    """Get the live ToolRegistry from the running FastAPI app."""
    from app.main import app
    return app.state.tool_registry


class ToolCreatorTool(BaseTool):
    """Built-in tool that lets agents create, update, and list custom tools.
    
    After DB operations, this tool also registers/unregisters tools
    in the live ToolRegistry so they are immediately available to agents.
    """

    @property
    def name(self) -> str:
        return "tool_creator"

    @property
    def description(self) -> str:
        return (
            "Create, update, or list custom tools that agents can use. "
            "Custom tools are Python scripts that receive a `params` dict and print output to stdout. "
            "Use action='create' to make a new tool, 'update' to modify one, 'list' to see all, or 'delete' to remove one. "
            "Created tools are immediately available for use by all agents."
        )

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "update", "list", "delete"],
                    "description": "The action to perform.",
                },
                "name": {
                    "type": "string",
                    "description": "Name of the tool (snake_case). Required for create/update/delete.",
                },
                "description": {
                    "type": "string",
                    "description": "Human-readable description of what the tool does. Required for create.",
                },
                "parameters_schema": {
                    "type": "string",
                    "description": 'JSON Schema string describing the tool\'s parameters. Example: \'{"type":"object","properties":{"query":{"type":"string","description":"Search query"}},"required":["query"]}\'',
                },
                "code": {
                    "type": "string",
                    "description": "Python code for the tool. It receives a `params` dict and should print output. Required for create.",
                },
            },
            "required": ["action"],
        }

    async def execute(self, action: str, name: str = "", description: str = "",
                      parameters_schema: str = "", code: str = "", **kwargs) -> str:
        from app.db.engine import async_session
        from app.services.custom_tool_service import CustomToolService, DynamicTool
        from sqlalchemy import select
        from app.models.custom_tool import CustomTool

        registry = _get_registry()

        async with async_session() as session:
            svc = CustomToolService(session)

            if action == "list":
                tools = await svc.list_all()
                if not tools:
                    return "No custom tools exist yet. Use action='create' to make one."
                lines = []
                for t in tools:
                    status = "active" if t.is_active else "inactive"
                    lines.append(f"- {t.name} ({status}): {t.description}")
                return "Custom tools:\n" + "\n".join(lines)

            elif action == "create":
                if not name or not description or not code:
                    return "Error: 'name', 'description', and 'code' are required for create."
                schema = parameters_schema or '{"type":"object","properties":{},"required":[]}'
                try:
                    json.loads(schema)
                except json.JSONDecodeError as e:
                    return f"Error: parameters_schema is not valid JSON: {e}"
                ct = await svc.create(
                    name=name, description=description,
                    parameters_schema=schema, code=code, is_active=True
                )
                # Register in live ToolRegistry so agents can use it immediately
                registry.register(DynamicTool(ct))
                return f"Tool '{ct.name}' created and registered successfully (id: {ct.id}). It is now active and available to all agents."

            elif action == "update":
                if not name:
                    return "Error: 'name' is required for update."
                result = await session.execute(select(CustomTool).where(CustomTool.name == name))
                ct = result.scalar_one_or_none()
                if not ct:
                    return f"Error: Tool '{name}' not found."
                updates = {}
                if description:
                    updates["description"] = description
                if parameters_schema:
                    try:
                        json.loads(parameters_schema)
                    except json.JSONDecodeError as e:
                        return f"Error: parameters_schema is not valid JSON: {e}"
                    updates["parameters_schema"] = parameters_schema
                if code:
                    updates["code"] = code
                if not updates:
                    return "Error: Provide at least one field to update (description, parameters_schema, code)."
                ct = await svc.update(ct.id, **updates)
                # Re-register updated tool in the live registry
                registry.unregister(name)
                registry.register(DynamicTool(ct))
                return f"Tool '{name}' updated and re-registered successfully."

            elif action == "delete":
                if not name:
                    return "Error: 'name' is required for delete."
                result = await session.execute(select(CustomTool).where(CustomTool.name == name))
                ct = result.scalar_one_or_none()
                if not ct:
                    return f"Error: Tool '{name}' not found."
                await svc.delete(ct.id)
                # Unregister from live ToolRegistry
                registry.unregister(name)
                return f"Tool '{name}' deleted and unregistered."

            else:
                return f"Error: Unknown action '{action}'. Use create, update, list, or delete."
