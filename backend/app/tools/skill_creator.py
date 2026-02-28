from app.tools.base import BaseTool


class SkillCreatorTool(BaseTool):
    """Built-in tool that lets agents create, update, and manage skills."""

    @property
    def name(self) -> str:
        return "skill_creator"

    @property
    def description(self) -> str:
        return (
            "Create, update, list, or delete skills. Skills are instruction sets (OpenClaw SKILL.md compatible) "
            "that guide agent behavior. Active skills are automatically injected into all agent system prompts. "
            "Use action='create' to make a new skill, 'update' to modify, 'list' to see all, 'import' to import "
            "from SKILL.md content, or 'delete' to remove one."
        )

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "update", "list", "delete", "import"],
                    "description": "The action to perform.",
                },
                "name": {
                    "type": "string",
                    "description": "Name of the skill. Required for create/update/delete.",
                },
                "description": {
                    "type": "string",
                    "description": "Brief description of the skill. Required for create.",
                },
                "instructions": {
                    "type": "string",
                    "description": "Detailed markdown instructions for the skill. Required for create.",
                },
                "is_active": {
                    "type": "boolean",
                    "description": "Whether the skill is active (defaults to true).",
                },
                "content": {
                    "type": "string",
                    "description": "Raw SKILL.md content for the 'import' action.",
                },
            },
            "required": ["action"],
        }

    async def execute(self, action: str, name: str = "", description: str = "",
                      instructions: str = "", is_active: bool = True,
                      content: str = "", **kwargs) -> str:
        from app.db.engine import async_session
        from app.services.skill_service import SkillService
        from sqlalchemy import select
        from app.models.skill import Skill

        async with async_session() as session:
            svc = SkillService(session)

            if action == "list":
                skills = await svc.list_all()
                if not skills:
                    return "No skills exist yet. Use action='create' to make one."
                lines = []
                for s in skills:
                    status = "active" if s.is_active else "inactive"
                    desc = s.description or "No description"
                    lines.append(f"- {s.name} ({status}): {desc}")
                return "Skills:\n" + "\n".join(lines)

            elif action == "create":
                if not name or not instructions:
                    return "Error: 'name' and 'instructions' are required for create."
                skill = await svc.create(
                    name=name, description=description or None,
                    instructions=instructions, is_active=is_active,
                    user_invocable=True
                )
                return f"Skill '{skill.name}' created successfully (id: {skill.id}). It is now {'active' if is_active else 'inactive'}."

            elif action == "update":
                if not name:
                    return "Error: 'name' is required for update."
                result = await session.execute(select(Skill).where(Skill.name == name))
                skill = result.scalar_one_or_none()
                if not skill:
                    return f"Error: Skill '{name}' not found."
                updates = {}
                if description:
                    updates["description"] = description
                if instructions:
                    updates["instructions"] = instructions
                if "is_active" in kwargs or is_active is not True:
                    updates["is_active"] = is_active
                if not updates:
                    return "Error: Provide at least one field to update."
                await svc.update(skill.id, **updates)
                return f"Skill '{name}' updated successfully."

            elif action == "delete":
                if not name:
                    return "Error: 'name' is required for delete."
                result = await session.execute(select(Skill).where(Skill.name == name))
                skill = result.scalar_one_or_none()
                if not skill:
                    return f"Error: Skill '{name}' not found."
                await svc.delete(skill.id)
                return f"Skill '{name}' deleted."

            elif action == "import":
                if not content:
                    return "Error: 'content' is required for import. Provide raw SKILL.md text."
                skill = await svc.import_from_content(content)
                return f"Skill '{skill.name}' imported successfully (id: {skill.id})."

            else:
                return f"Error: Unknown action '{action}'. Use create, update, list, delete, or import."
