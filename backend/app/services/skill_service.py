import json
import httpx

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

    async def import_from_github_url(self, slug_or_url: str) -> Skill:
        """Import a skill by providing its ClawHub slug or a full GitHub URL.
        
        A slug (e.g., 'academic-research') maps to:
        https://raw.githubusercontent.com/openclaw/skills/main/skills/{author}/{slug}/SKILL.md
        
        A URL (e.g., 'https://github.com/user/repo') maps to:
        https://raw.githubusercontent.com/user/repo/main/SKILL.md
        """
        slug_or_url = slug_or_url.strip()
        
        async with httpx.AsyncClient() as client:
            if slug_or_url.startswith("http://") or slug_or_url.startswith("https://"):
                # Assume it's a full GitHub URL
                url = slug_or_url
                if "github.com" in url and "raw.githubusercontent.com" not in url:
                    url = url.replace("github.com", "raw.githubusercontent.com")
                    url = f"{url}/main/SKILL.md"
                elif "raw.githubusercontent.com" in url and not url.endswith(".md"):
                    url = f"{url}/SKILL.md"
            else:
                # Assume it's an OpenClaw slug. We need to find the author directory first.
                tree_url = "https://api.github.com/repos/openclaw/skills/git/trees/main?recursive=1"
                try:
                    tree_resp = await client.get(tree_url, headers={"User-Agent": "Assitance-AI"})
                    tree_resp.raise_for_status()
                    tree_data = tree_resp.json()
                    
                    # Search for skills/{author}/{slug}/SKILL.md
                    target_path = None
                    # The slug isn't guaranteed to be the exact folder name 
                    # but usually it's author/slug/SKILL.md or author/slug-something/SKILL.md
                    slug_lower = slug_or_url.lower()
                    for item in tree_data.get("tree", []):
                        path = item.get("path", "")
                        if path.startswith("skills/") and path.endswith("SKILL.md"):
                            # Extrct the folder name just before SKILL.md
                            parts = path.split("/")
                            if len(parts) >= 3:
                                folder_name = parts[-2].lower()
                                if folder_name == slug_lower or slug_lower in folder_name:
                                    target_path = path
                                    break
                    
                    if not target_path:
                        raise ValueError(f"Skill slug '{slug_or_url}' not found in the OpenClaw skills registry.")
                        
                    url = f"https://raw.githubusercontent.com/openclaw/skills/main/{target_path}"
                except Exception as e:
                    if isinstance(e, ValueError):
                        raise
                    raise ValueError(f"Failed to query OpenClaw skills registry: {e}")

            response = await client.get(url, follow_redirects=True)
            if response.status_code != 200:
                raise ValueError(f"Failed to fetch SKILL.md from {url}. Status: {response.status_code}")
            
            content = response.text
            return await self.import_from_content(content)

    def render_instructions(self, skills: list[Skill]) -> str:
        """Return combined instructions from a list of skills."""
        if not skills:
            return ""
        parts = []
        for s in skills:
            header = f"## Skill: {s.name}"
            if s.description:
                header += f"\n{s.description}"
            parts.append(f"{header}\n\n{s.instructions}")
        return "\n\n---\n\n".join(parts)

    async def get_active_skills(self) -> list[Skill]:
        result = await self.session.execute(
            select(Skill).where(Skill.is_active).order_by(Skill.name)
        )
        return list(result.scalars().all())

    async def get_active_instructions(self) -> str:
        """Return combined instructions from all active skills, for system prompt injection."""
        skills = await self.get_active_skills()
        return self.render_instructions(skills)

    async def update_skill_metrics(self, skill_id: str, success: bool, cost: float = 0.0, duration: float = 0.0):
        """Update execution metrics for a skill."""
        from app.models.skill import Skill
        skill = await self.session.get(Skill, skill_id)
        if not skill:
            return
        if success:
            skill.success_count = (skill.success_count or 0) + 1
        else:
            skill.failure_count = (skill.failure_count or 0) + 1
        skill.total_execution_cost = (skill.total_execution_cost or 0.0) + cost
        skill.usage_frequency = (skill.usage_frequency or 0) + 1
        await self.session.commit()

    async def get_skill_performance(self, skill_id: str) -> dict | None:
        """Get performance metrics for a skill."""
        from app.models.skill import Skill
        skill = await self.session.get(Skill, skill_id)
        if not skill:
            return None
        total = (skill.success_count or 0) + (skill.failure_count or 0)
        success_rate = (skill.success_count or 0) / max(total, 1)
        return {
            "skill_id": skill_id,
            "success_rate": round(success_rate, 3),
            "total_executions": total,
            "success_count": skill.success_count or 0,
            "failure_count": skill.failure_count or 0,
            "total_cost": skill.total_execution_cost or 0.0,
            "usage_frequency": skill.usage_frequency or 0,
        }

    async def auto_disable_check(self):
        """Disable skills with <50% success rate after 10+ uses."""
        from app.models.skill import Skill
        from sqlalchemy import select
        stmt = select(Skill).where(Skill.is_active == True)
        result = await self.session.execute(stmt)
        skills = result.scalars().all()
        disabled = 0
        for skill in skills:
            total = (skill.success_count or 0) + (skill.failure_count or 0)
            if total >= 10:
                success_rate = (skill.success_count or 0) / total
                if success_rate < 0.5:
                    skill.is_active = False
                    disabled += 1
        if disabled > 0:
            await self.session.commit()
        return disabled

    async def find_relevant_skills(self, task_description: str, limit: int = 5) -> list:
        """Find skills relevant to a task description using keyword matching."""
        from app.models.skill import Skill
        from sqlalchemy import select
        stmt = select(Skill).where(Skill.is_active == True)
        result = await self.session.execute(stmt)
        skills = result.scalars().all()

        # Simple keyword overlap scoring
        task_words = set(task_description.lower().split())
        scored = []
        for skill in skills:
            skill_words = set((skill.name + " " + (skill.description or "")).lower().split())
            overlap = len(task_words & skill_words)
            if overlap > 0:
                scored.append((overlap, skill))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:limit]]

    async def get_shared_skills(self) -> list:
        """Get all approved/deployed skills available to any agent."""
        from app.models.skill import Skill
        from sqlalchemy import select
        stmt = select(Skill).where(
            Skill.is_active == True,
            Skill.lifecycle_stage.in_(["approved", "deployed"])
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
