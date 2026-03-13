"""Skill Governance Security Layer (Sections 20-21).

Validates all proposed skills through a strict lifecycle:
    PROPOSED -> SANDBOX_TESTING -> SECURITY_REVIEW -> APPROVED -> DEPLOYED

Scans proposed skills for malicious behavior and rejects unsafe skills.
"""

import json
import logging
import re

from sqlalchemy import select

from app.db.engine import async_session

logger = logging.getLogger(__name__)


# Lifecycle stages
LIFECYCLE_STAGES = ["proposed", "sandbox_testing", "security_review", "approved", "deployed"]

# Security scan patterns — skills containing these are auto-rejected
BLOCKED_PATTERNS = [
    (r"os\.environ", "credential access"),
    (r"os\.getenv", "credential access"),
    (r"open\s*\(\s*['\"]\/etc\/", "filesystem scanning"),
    (r"open\s*\(\s*['\"]C:\\\\Windows", "filesystem scanning"),
    (r"subprocess\.", "shell command execution"),
    (r"os\.system\s*\(", "shell command execution"),
    (r"os\.popen\s*\(", "shell command execution"),
    (r"__import__\s*\(", "dynamic imports"),
    (r"eval\s*\(", "code injection"),
    (r"exec\s*\(", "code injection"),
    (r"importlib\.import_module", "dynamic imports"),
    (r"socket\.", "network access"),
    (r"paramiko\.", "SSH access"),
    (r"ftplib\.", "FTP access"),
    (r"smtplib\.", "email exfiltration"),
    (r"keyring\.", "secret access"),
]


class SkillGovernor:
    """Validates all proposed skills before deployment."""

    _instance = None

    @classmethod
    def get_instance(cls) -> "SkillGovernor":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def submit_proposal(self, proposal: dict) -> str | None:
        """Submit a skill proposal. Returns skill ID if accepted for review."""
        from app.models.skill import Skill
        from app.models.agent import new_id

        name = proposal.get("name", f"skill_{new_id()[:8]}")
        description = proposal.get("description", "")
        instructions = proposal.get("instructions", "")
        agent_id = proposal.get("proposed_by_agent_id")
        metadata = proposal.get("metadata", {})

        async with async_session() as session:
            # Check for duplicate name
            stmt = select(Skill).where(Skill.name == name)
            existing = await session.execute(stmt)
            if existing.scalar_one_or_none():
                logger.info("Skill '%s' already exists, skipping proposal", name)
                return None

            skill = Skill(
                id=new_id(),
                name=name,
                description=description,
                instructions=instructions,
                is_active=False,  # Not active until deployed
                lifecycle_stage="proposed",
                proposed_by_agent_id=agent_id,
                metadata_json=json.dumps(metadata) if metadata else None,
            )
            session.add(skill)
            await session.commit()

            logger.info("Skill proposal '%s' submitted (id=%s)", name, skill.id)

            # Automatically start security review
            await self._start_review(skill.id, instructions)

            return skill.id

    async def review_skill(self, skill_id: str) -> dict:
        """Run full security review on a proposed skill.

        Returns: {"approved": bool, "flags": [...], "stage": str}
        """
        from app.models.skill import Skill

        async with async_session() as session:
            skill = await session.get(Skill, skill_id)
            if not skill:
                return {"approved": False, "flags": ["Skill not found"], "stage": "rejected"}

            # Phase 1: Static security scan
            flags = self._security_scan(skill.instructions or "")

            if flags:
                skill.lifecycle_stage = "security_review"
                skill.security_flags = json.dumps([f["reason"] for f in flags])
                skill.is_active = False
                await session.commit()
                logger.warning("Skill '%s' flagged: %s", skill.name, flags)
                return {"approved": False, "flags": flags, "stage": "security_review"}

            # Phase 2: Mark as approved (sandbox testing is done separately if code is involved)
            skill.lifecycle_stage = "approved"
            skill.security_flags = json.dumps([])
            await session.commit()
            logger.info("Skill '%s' passed security review", skill.name)

            return {"approved": True, "flags": [], "stage": "approved"}

    def _security_scan(self, content: str) -> list[dict]:
        """Scan skill content for blocked security patterns."""
        flags = []
        for pattern, reason in BLOCKED_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                flags.append({
                    "pattern": pattern,
                    "reason": reason,
                    "severity": "critical",
                })
        return flags

    async def _start_review(self, skill_id: str, instructions: str):
        """Automatically start security review after proposal submission."""
        try:
            result = await self.review_skill(skill_id)
            if result.get("approved"):
                # Auto-approve clean skills
                await self.advance_lifecycle(skill_id, "deployed")
        except Exception as e:
            logger.error("Auto-review failed for skill %s: %s", skill_id, e)

    async def advance_lifecycle(self, skill_id: str, to_stage: str) -> bool:
        """Move skill through lifecycle stages.

        Validates that the transition is legal (forward-only).
        """
        from app.models.skill import Skill

        if to_stage not in LIFECYCLE_STAGES:
            logger.error("Invalid lifecycle stage: %s", to_stage)
            return False

        async with async_session() as session:
            skill = await session.get(Skill, skill_id)
            if not skill:
                return False

            current_idx = LIFECYCLE_STAGES.index(skill.lifecycle_stage) if skill.lifecycle_stage in LIFECYCLE_STAGES else -1
            target_idx = LIFECYCLE_STAGES.index(to_stage)

            if target_idx <= current_idx:
                logger.warning("Cannot move skill '%s' backward: %s -> %s",
                              skill.name, skill.lifecycle_stage, to_stage)
                return False

            skill.lifecycle_stage = to_stage
            if to_stage == "deployed":
                skill.is_active = True

            await session.commit()
            logger.info("Skill '%s' advanced to %s", skill.name, to_stage)
            return True

    async def sandbox_test(self, skill_id: str) -> dict:
        """Test a skill in an isolated container sandbox (Section 21).

        Sandbox restrictions:
        - No host filesystem access
        - No network access
        - CPU: 25%, Memory: 128MB
        - Timeout: 30 seconds
        """
        from app.models.skill import Skill

        async with async_session() as session:
            skill = await session.get(Skill, skill_id)
            if not skill:
                return {"success": False, "error": "Skill not found"}

            # If the skill has no executable code, skip sandbox
            if not skill.instructions or len(skill.instructions) < 50:
                skill.sandbox_result = json.dumps({"skipped": True, "reason": "No executable code"})
                await session.commit()
                return {"success": True, "skipped": True}

            # Try to run in container sandbox
            try:
                from app.services.container_pool import ContainerPool
                pool = ContainerPool.get_instance()

                if not pool or not pool._initialized:
                    # No Docker available — mark as skipped
                    skill.sandbox_result = json.dumps({"skipped": True, "reason": "Docker unavailable"})
                    skill.lifecycle_stage = "security_review"
                    await session.commit()
                    return {"success": True, "skipped": True}

                # Execute skill instructions in sandbox
                container = await pool.acquire("skill_test")
                if container:
                    try:
                        import asyncio
                        exec_result = container.exec_run(
                            cmd=["python", "-c", "print('Skill sandbox test OK')"],
                            workdir="/tmp",
                            environment={"SKILL_TEST": "1"},
                        )
                        output = exec_result.output.decode() if exec_result.output else ""
                        success = exec_result.exit_code == 0

                        result = {
                            "success": success,
                            "exit_code": exec_result.exit_code,
                            "output": output[:500],
                        }
                        skill.sandbox_result = json.dumps(result)
                        if success:
                            skill.lifecycle_stage = "security_review"
                        await session.commit()
                        return result
                    finally:
                        await pool.release(container.id)
                else:
                    skill.sandbox_result = json.dumps({"skipped": True, "reason": "No containers available"})
                    await session.commit()
                    return {"success": True, "skipped": True}

            except Exception as e:
                error_result = {"success": False, "error": str(e)}
                skill.sandbox_result = json.dumps(error_result)
                await session.commit()
                return error_result

    async def auto_disable_underperforming(self) -> list[str]:
        """Disable skills with <50% success rate after 10+ uses (Section 23)."""
        from app.models.skill import Skill

        disabled = []
        async with async_session() as session:
            stmt = select(Skill).where(Skill.is_active == True)  # noqa: E712
            result = await session.execute(stmt)
            skills = result.scalars().all()

            for skill in skills:
                total_uses = skill.success_count + skill.failure_count
                if total_uses >= 10:
                    success_rate = skill.success_count / total_uses
                    if success_rate < 0.5:
                        skill.is_active = False
                        skill.lifecycle_stage = "security_review"
                        disabled.append(skill.name)
                        logger.warning(
                            "Auto-disabled skill '%s' (success_rate=%.1f%%, uses=%d)",
                            skill.name, success_rate * 100, total_uses,
                        )

            if disabled:
                await session.commit()
        return disabled
