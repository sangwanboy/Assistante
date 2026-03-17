from app.tools.base import BaseTool
import json
import logging
from typing import Optional
from sqlalchemy import select
from app.models.agent_schedule import AgentSchedule
from app.db.engine import async_session

logger = logging.getLogger(__name__)

class ScheduleTool(BaseTool):
    """Tool for agents to manage their own heartbeat schedules."""
    
    @property
    def name(self) -> str:
        return "manage_schedules"

    @property
    def description(self) -> str:
        return (
            "Manage heartbeat-driven recurring tasks. "
            "Use this to set up a 'heartbeat' (e.g., check something every 10 minutes) "
            "for yourself OR for another agent. "
            "When the heartbeat fires, the agent will be prompted in their own conversation."
        )

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "The action to perform: 'create', 'list', 'update', or 'delete'",
                    "enum": ["create", "list", "update", "delete"]
                },
                "target_agent_id": {
                    "type": "string",
                    "description": "Optional UUID of the target agent to manage schedules for. Defaults to you."
                },
                "target_agent_name": {
                    "type": "string",
                    "description": "Optional name of the target agent (worker). Use this if you don't have the ID."
                },
                "name": {
                    "type": "string",
                    "description": "Optional name for the schedule (required for 'create')"
                },
                "interval_minutes": {
                    "type": "integer",
                    "description": "How often to fire in minutes (default: 60, min: 2). Used for create and update.",
                    "default": 60
                },
                "prompt": {
                    "type": "string",
                    "description": "The prompt to send to the target agent when the heartbeat fires (required for 'create')"
                },
                "schedule_id": {
                    "type": "string",
                    "description": "The ID of the schedule (required for 'delete' and 'update')"
                }
            },
            "required": ["action"]
        }

    async def execute(self, action: str, **kwargs) -> str:
        logger.info(f"ScheduleTool.execute called with action='{action}', kwargs={list(kwargs.keys())}")
        
        # 1. Determine origin agent (the one calling the tool)
        origin_agent_id = kwargs.get("_agent_id") or kwargs.get("agent_id")
        if not origin_agent_id:
            return "Error: agent_id not provided in execution context."

        # 2. Resolve target agent
        target_agent_id = kwargs.get("target_agent_id")
        target_agent_name = kwargs.get("target_agent_name")
        
        async with async_session() as session:
            final_target_id = origin_agent_id
            target_display_name = "you"

            if target_agent_id or target_agent_name:
                from app.models.agent import Agent
                from sqlalchemy import func

                if target_agent_id:
                    target = await session.get(Agent, target_agent_id)
                else:
                    stmt = select(Agent).where(func.lower(Agent.name) == target_agent_name.lower())
                    result = await session.execute(stmt)
                    target = result.scalar_one_or_none()
                
                if not target:
                    return f"Error: Could not find target agent matching '{target_agent_id or target_agent_name}'."
                
                final_target_id = target.id
                target_display_name = target.name

            # 3. Perform action for the final_target_id
            if action == "create":
                name = kwargs.get("name")
                prompt = kwargs.get("prompt")
                interval = max(kwargs.get("interval_minutes", 60), 2)
                
                if not name or not prompt:
                    return "Error: 'name' and 'prompt' are required to create a schedule."
                
                sched = AgentSchedule(
                    agent_id=final_target_id,
                    name=name,
                    interval_minutes=interval,
                    task_config_json=json.dumps({
                        "prompt": prompt,
                        "conversation_id": kwargs.get("conversation_id"),
                    }),
                    is_active=True
                )
                session.add(sched)
                await session.commit()
                await session.refresh(sched)
                return f"Successfully created schedule '{name}' (ID: {sched.id}) for {target_display_name}, firing every {interval} minutes."

            elif action == "list":
                stmt = select(AgentSchedule).where(AgentSchedule.agent_id == final_target_id)
                result = await session.execute(stmt)
                schedules = result.scalars().all()
                if not schedules:
                    return f"No active schedules found for {target_display_name}."
                
                out = [f"Active Schedules for {target_display_name}:"]
                for s in schedules:
                    status = "active" if s.is_active else "paused"
                    out.append(f"- [{status}] {s.name} (ID: {s.id}) - Every {s.interval_minutes}m, Last run: {s.last_run or 'Never'}")
                return "\n".join(out)

            elif action == "update":
                sid = kwargs.get("schedule_id")
                if not sid:
                    return "Error: 'schedule_id' is required to update a schedule."
                
                # Use target agent for security/consistency check
                stmt = select(AgentSchedule).where(AgentSchedule.id == sid, AgentSchedule.agent_id == final_target_id)
                result = await session.execute(stmt)
                sched = result.scalar_one_or_none()
                if not sched:
                    return f"Error: No schedule found with ID '{sid}' belonging to {target_display_name}."
                
                updated_fields = []
                if "name" in kwargs and kwargs["name"]:
                    sched.name = kwargs["name"]
                    updated_fields.append("name")
                
                if "interval_minutes" in kwargs:
                    interval = max(kwargs["interval_minutes"], 2)
                    sched.interval_minutes = interval
                    updated_fields.append("interval_minutes")
                    
                if "prompt" in kwargs and kwargs["prompt"]:
                    try:
                        config = json.loads(sched.task_config_json or "{}")
                    except json.JSONDecodeError:
                        config = {}
                    config["prompt"] = kwargs["prompt"]
                    sched.task_config_json = json.dumps(config)
                    updated_fields.append("prompt")
                
                if not updated_fields:
                    return "No fields provided to update. Please provide 'name', 'interval_minutes', or 'prompt'."
                    
                await session.commit()
                return f"Successfully updated schedule {sid} for {target_display_name}. Fields updated: {', '.join(updated_fields)}."

            elif action == "delete":
                sid = kwargs.get("schedule_id")
                name = kwargs.get("name")
                
                if not sid and not name:
                    return "Error: Either 'schedule_id' or 'name' is required to delete a schedule."
                
                if sid:
                    stmt = select(AgentSchedule).where(AgentSchedule.id == sid, AgentSchedule.agent_id == final_target_id)
                else:
                    stmt = select(AgentSchedule).where(AgentSchedule.name == name, AgentSchedule.agent_id == final_target_id)
                    
                result = await session.execute(stmt)
                sched = result.scalar_one_or_none()
                if not sched:
                    target_ref = f"ID '{sid}'" if sid else f"name '{name}'"
                    return f"Error: No schedule found with {target_ref} belonging to {target_display_name}."
                
                deleted_id = sched.id
                deleted_name = sched.name
                await session.delete(sched)
                await session.commit()
                return f"Successfully deleted schedule '{deleted_name}' (ID: {deleted_id}) for {target_display_name}."

            return f"Error: Unknown action '{action}'."
