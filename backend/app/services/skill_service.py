import json
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill import Skill


def parse_skill_md(content: str) -> dict:
    """Parse an OpenClaw-format SKILL.md file.

    Expected format:
    ---
    name: My Skill
    description: Does something useful
    user-invocable: true
    trigger: "**/*.py"
    homepage: https://example.com
    ---
    # Instructions body in markdown
    ...
    """
    result: dict = {
        "name": "",
        "description": None,
        "instructions": "",
        "user_invocable": True,
        "trigger_pattern": None,
        "metadata_json": None,
    }

    content = content.strip()

    # Check for YAML front-matter delimiters
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1].strip()
            body = parts[2].strip()
        else:
            frontmatter = ""
            body = content
    else:
        frontmatter = ""
        body = content

    result["instructions"] = body

    # Parse YAML-like frontmatter (simple key: value pairs)
    extra_meta: dict = {}
    if frontmatter:
        for line in frontmatter.split("\n"):
            line = line.strip()
            if not line or ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip().lower()
            value = value.strip().strip('"').strip("'")

            if key == "name":
                result["name"] = value
            elif key == "description":
                result["description"] = value
            elif key == "user-invocable":
                result["user_invocable"] = value.lower() in ("true", "yes", "1")
            elif key == "disable-model-invocation":
                # OpenClaw compat: inverse
                pass
            elif key == "trigger":
                result["trigger_pattern"] = value
            else:
                extra_meta[key] = value

    if extra_meta:
        result["metadata_json"] = json.dumps(extra_meta)

    return result


def export_skill_md(skill: Skill) -> str:
    """Generate OpenClaw-format SKILL.md content from a Skill record."""
    lines = ["---"]
    lines.append(f"name: {skill.name}")
    if skill.description:
        lines.append(f"description: {skill.description}")
    lines.append(f"user-invocable: {'true' if skill.user_invocable else 'false'}")
    if skill.trigger_pattern:
        lines.append(f'trigger: "{skill.trigger_pattern}"')

    # Add extra metadata
    if skill.metadata_json:
        try:
            meta = json.loads(skill.metadata_json)
            for k, v in meta.items():
                lines.append(f"{k}: {v}")
        except (json.JSONDecodeError, TypeError):
            pass

    lines.append("---")
    lines.append("")
    lines.append(skill.instructions or "")
    return "\n".join(lines)


class SkillService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(self) -> list[Skill]:
        result = await self.session.execute(
            select(Skill).order_by(Skill.created_at.desc())
        )
        return list(result.scalars().all())

    async def get(self, skill_id: str) -> Skill | None:
        return await self.session.get(Skill, skill_id)

    async def create(self, **kwargs) -> Skill:
        skill = Skill(**kwargs)
        self.session.add(skill)
        await self.session.commit()
        await self.session.refresh(skill)
        return skill

    async def update(self, skill_id: str, **kwargs) -> Skill | None:
        skill = await self.get(skill_id)
        if not skill:
            return None
        for k, v in kwargs.items():
            if v is not None:
                setattr(skill, k, v)
        await self.session.commit()
        await self.session.refresh(skill)
        return skill

    async def delete(self, skill_id: str) -> bool:
        skill = await self.get(skill_id)
        if not skill:
            return False
        await self.session.delete(skill)
        await self.session.commit()
        return True

    async def import_from_content(self, content: str) -> Skill:
        """Import a skill from raw SKILL.md content."""
        parsed = parse_skill_md(content)
        if not parsed["name"]:
            parsed["name"] = "Imported Skill"
        return await self.create(**parsed)

    async def get_active_skills(self) -> list[Skill]:
        result = await self.session.execute(
            select(Skill).where(Skill.is_active == True).order_by(Skill.name)
        )
        return list(result.scalars().all())

    async def get_active_instructions(self) -> str:
        """Return combined instructions from all active skills, for system prompt injection."""
        skills = await self.get_active_skills()
        if not skills:
            return ""
        parts = []
        for s in skills:
            header = f"## Skill: {s.name}"
            if s.description:
                header += f"\n{s.description}"
            parts.append(f"{header}\n\n{s.instructions}")
        return "\n\n---\n\n".join(parts)
