"""Agent Capability Registry (Section 3).

Centralized capability index enabling similarity-based task routing
instead of simple role-based matching.
"""

import json
import logging
from dataclasses import dataclass, field

from sqlalchemy import select

from app.db.engine import async_session

logger = logging.getLogger(__name__)


# Default capability keywords for extraction
CAPABILITY_KEYWORDS = {
    "coding": ["code", "program", "develop", "build", "implement", "debug", "fix", "script", "software"],
    "research": ["research", "search", "find", "investigate", "analyze", "study", "explore", "discover"],
    "writing": ["write", "draft", "compose", "create content", "document", "summarize", "report"],
    "data_analysis": ["data", "analyze", "statistics", "chart", "graph", "metric", "dashboard", "csv"],
    "design": ["design", "ui", "ux", "layout", "visual", "style", "theme", "mockup"],
    "devops": ["deploy", "docker", "container", "ci/cd", "pipeline", "infrastructure", "server"],
    "testing": ["test", "qa", "quality", "verify", "validate", "assertion", "coverage"],
    "orchestration": ["orchestrate", "coordinate", "manage", "delegate", "plan", "organize"],
    "communication": ["communicate", "message", "notify", "announce", "broadcast", "email"],
    "file_management": ["file", "directory", "folder", "upload", "download", "storage"],
}


@dataclass
class AgentCapabilityProfile:
    """Structured capability profile for an agent."""
    agent_id: str
    agent_name: str
    skills: list[str] = field(default_factory=list)
    supported_tools: list[str] = field(default_factory=list)
    domain_expertise: list[str] = field(default_factory=list)
    supported_models: list[str] = field(default_factory=list)
    success_rate: float = 1.0
    is_system: bool = False


class CapabilityRegistry:
    """Centralized capability index for task routing."""

    _instance = None

    @classmethod
    def get_instance(cls) -> "CapabilityRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def build_profile(self, agent) -> AgentCapabilityProfile:
        """Build a capability profile from an Agent ORM object."""
        capabilities = []
        if agent.capabilities:
            try:
                capabilities = json.loads(agent.capabilities)
            except (json.JSONDecodeError, TypeError):
                capabilities = []

        tools = []
        if agent.enabled_tools:
            try:
                tools = json.loads(agent.enabled_tools)
            except (json.JSONDecodeError, TypeError):
                tools = []

        skills = []
        if agent.enabled_skills:
            try:
                skills = json.loads(agent.enabled_skills)
            except (json.JSONDecodeError, TypeError):
                skills = []

        metrics = {}
        if agent.performance_metrics:
            try:
                metrics = json.loads(agent.performance_metrics)
            except (json.JSONDecodeError, TypeError):
                metrics = {}

        domain = capabilities.copy()
        if agent.role:
            domain.append(agent.role.lower())

        return AgentCapabilityProfile(
            agent_id=agent.id,
            agent_name=agent.name,
            skills=skills,
            supported_tools=tools,
            domain_expertise=domain,
            supported_models=[agent.model] if agent.model else [],
            success_rate=metrics.get("success_rate", 1.0),
            is_system=agent.is_system,
        )

    def extract_required_capabilities(self, task_description: str) -> list[str]:
        """Extract capability requirements from a task description using keyword matching."""
        task_lower = task_description.lower()
        required = []
        for capability, keywords in CAPABILITY_KEYWORDS.items():
            if any(kw in task_lower for kw in keywords):
                required.append(capability)
        return required if required else ["general"]

    def score_agent(
        self,
        profile: AgentCapabilityProfile,
        required_capabilities: list[str],
        required_tools: list[str] | None = None,
    ) -> float:
        """Score an agent against required capabilities.

        Scoring:
        - Domain expertise overlap: 40% weight
        - Tool coverage: 30% weight
        - Success rate: 30% weight
        """
        if not required_capabilities:
            return profile.success_rate

        # Domain expertise overlap
        domain_set = set(profile.domain_expertise)
        required_set = set(required_capabilities)
        domain_overlap = len(domain_set & required_set) / max(len(required_set), 1)

        # Tool coverage
        tool_score = 1.0
        if required_tools:
            tool_set = set(profile.supported_tools)
            tool_overlap = len(tool_set & set(required_tools)) / max(len(required_tools), 1)
            tool_score = tool_overlap

        # Weighted score
        score = (
            0.4 * domain_overlap
            + 0.3 * tool_score
            + 0.3 * profile.success_rate
        )
        return score

    async def find_best_agent(
        self,
        task_description: str,
        required_capabilities: list[str] | None = None,
        required_tools: list[str] | None = None,
        exclude_agent_ids: list[str] | None = None,
    ):
        """Find the best agent for a task using capability similarity scoring.

        Returns the Agent ORM object with the highest score, or None.
        """
        from app.models.agent import Agent

        if required_capabilities is None:
            required_capabilities = self.extract_required_capabilities(task_description)

        exclude_ids = set(exclude_agent_ids or [])

        async with async_session() as session:
            stmt = select(Agent).where(Agent.is_active == True, Agent.is_system == False)  # noqa: E712
            result = await session.execute(stmt)
            agents = result.scalars().all()

        best_agent = None
        best_score = -1.0

        for agent in agents:
            if agent.id in exclude_ids:
                continue

            profile = await self.build_profile(agent)
            score = self.score_agent(profile, required_capabilities, required_tools)

            logger.debug(
                "Capability score for %s: %.3f (caps=%s)",
                agent.name, score, required_capabilities,
            )

            if score > best_score:
                best_score = score
                best_agent = agent

        if best_agent:
            logger.info(
                "Best agent for task: %s (score=%.3f, caps=%s)",
                best_agent.name, best_score, required_capabilities,
            )

        return best_agent

    async def get_agent_capabilities(self, agent_id: str) -> AgentCapabilityProfile | None:
        """Return full capability profile for a specific agent."""
        from app.models.agent import Agent

        async with async_session() as session:
            agent = await session.get(Agent, agent_id)
            if not agent:
                return None
            return await self.build_profile(agent)

    async def register_agent_capabilities(
        self,
        agent_id: str,
        capabilities: list[str],
    ) -> None:
        """Update an agent's declared capabilities in the database."""
        from app.models.agent import Agent

        async with async_session() as session:
            agent = await session.get(Agent, agent_id)
            if agent:
                agent.capabilities = json.dumps(capabilities)
                await session.commit()
                logger.info("Updated capabilities for agent %s: %s", agent.name, capabilities)

    async def update_performance_metrics(
        self,
        agent_id: str,
        success: bool,
        completion_time: float = 0.0,
    ) -> None:
        """Update agent performance metrics after task completion."""
        from app.models.agent import Agent

        async with async_session() as session:
            agent = await session.get(Agent, agent_id)
            if not agent:
                return

            metrics = {}
            if agent.performance_metrics:
                try:
                    metrics = json.loads(agent.performance_metrics)
                except (json.JSONDecodeError, TypeError):
                    metrics = {}

            completed = metrics.get("tasks_completed", 0)
            failed = metrics.get("tasks_failed", 0)

            if success:
                completed += 1
            else:
                failed += 1

            total = completed + failed
            metrics["tasks_completed"] = completed
            metrics["tasks_failed"] = failed
            metrics["success_rate"] = completed / total if total > 0 else 1.0

            # Rolling average completion time
            avg_time = metrics.get("avg_completion_time", 0)
            if completion_time > 0 and total > 0:
                metrics["avg_completion_time"] = (
                    (avg_time * (total - 1) + completion_time) / total
                )

            agent.performance_metrics = json.dumps(metrics)
            await session.commit()
