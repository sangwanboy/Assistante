import logging
import json
from app.models.agent import Agent
from app.models.task import Task
from app.services.brain_service import AgentBrainService
from app.providers.base import ChatMessage

logger = logging.getLogger(__name__)

class ReflectionService:
    """Analyzes a task's execution history to extract generalized learnings for the agent."""

    def __init__(self, session, providers):
        self.session = session
        self.providers = providers

    async def reflect_on_task(self, agent: Agent, task: Task, history: list[dict]):
        """Runs the LLM reflection and saves strategies to the agent's memory."""
        try:
            if not history:
                return

            # Default to the agent's configured model or openai fallback
            if "/" in agent.model:
                provider_name, model_id = agent.model.split("/", 1)
            else:
                provider_name, model_id = "openai", agent.model
                
            provider = self.providers.get(provider_name)
            if not provider:
                logger.warning(f"ReflectionService: Provider {provider_name} not found.")
                return

            # Build history summary
            history_text = ""
            for entry in history:
                step = entry.get("step", 0)
                tools = entry.get("tool_calls_in_step", 0)
                preview = entry.get("output_preview", "")
                history_text += f"Step {step} (Tools used: {tools}):\n{preview}\n\n"

            status_str = f"The task completed with status: {task.status}."
            
            prompt = (
                f"You are an AI agent introspecting on your recent past performance.\n\n"
                f"Task Goal: {task.goal or task.prompt}\n\n"
                f"Execution History:\n{history_text}\n"
                f"{status_str}\n\n"
                "Please analyze what went well and what could have been done better. "
                "Then, extract 0 to 2 generalized strategy rules or facts that you should remember for the future. "
                "These should be high-level insights, not specific data from this task. "
                "Respond ONLY with a JSON array of strings containing the rules. "
                "If there is nothing useful to learn, return an empty array []."
            )

            messages = [
                ChatMessage(
                    role="system",
                    content="You are a reflection engine. Output only valid JSON arrays of strings. No markdown formatting."
                ),
                ChatMessage(role="user", content=prompt),
            ]

            result = await provider.complete(messages, model_id, temperature=0.3)
            content = (result.content or "").strip()
            
            # Clean up potential markdown formatting code blocks
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            if not content or content == "[]":
                logger.info(f"Agent {agent.name} reflected on task {task.id} but extracted no new rules.")
                return

            try:
                rules = json.loads(content)
                if isinstance(rules, list) and rules:
                    for rule in rules:
                        if isinstance(rule, str) and rule.strip():
                            AgentBrainService.append_memory(agent.name, rule.strip())
                            logger.info(f"Agent {agent.name} learned a new strategy: {rule[:50]}...")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse reflection output as JSON: {e}\nOutput: {content}")

            # ── Skill Discovery Integration ──
            try:
                from app.services.skill_discovery import SkillDiscoveryService
                discovery = SkillDiscoveryService(self.session, self.providers)
                await discovery.analyze_task_completion(
                    agent_id=agent.id,
                    task=task,
                    steps=history,
                    outcome=task.status,
                )
            except Exception as skill_exc:
                logger.debug("Skill discovery skipped: %s", skill_exc)

        except Exception as exc:
            logger.error("Reflection failed for task %s: %s", task.id, exc, exc_info=True)
