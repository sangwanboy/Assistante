from typing import Any, Dict
from app.tools.base import BaseTool
import json

class CheckTaskStatusTool(BaseTool):
    """Tool for checking the status of a specific task."""
    
    @property
    def name(self) -> str:
        return "check_task_status"
        
    @property
    def description(self) -> str:
        return "Check the status and progress of a specific task."
    
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The ID of the task to check."
                }
            },
            "required": ["task_id"]
        }
        
    async def execute(self, **kwargs) -> Any:
        task_id = kwargs.get("task_id")
        if not task_id:
            return "Error: missing task_id"
            
        from app.db.engine import get_async_session
        from app.services.task_manager import TaskManager
        
        async with get_async_session() as session:
            tm = TaskManager(session)
            t = await tm.get_task(task_id)
            if not t:
                return f"Error: task {task_id} not found."
                
            return {
                "task_id": t.id,
                "status": t.status,
                "progress_percent": t.progress_percent,
                "assigned_agent": t.assigned_agent_id,
                "error": t.error_message
            }


class GetTaskTreeStatusTool(BaseTool):
    """Tool for checking the status of all subtasks of a parent task."""
    
    @property
    def name(self) -> str:
        return "get_task_tree_status"
        
    @property
    def description(self) -> str:
        return "Check the live status of an entire subtask tree under a parent task."
    
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "parent_task_id": {
                    "type": "string",
                    "description": "The ID of the parent orchestrator task."
                }
            },
            "required": ["parent_task_id"]
        }
        
    async def execute(self, **kwargs) -> Any:
        parent_task_id = kwargs.get("parent_task_id")
        if not parent_task_id:
            return "Error: missing parent_task_id"
            
        from app.db.engine import get_async_session
        from app.services.task_manager import TaskManager
        
        async with get_async_session() as session:
            tm = TaskManager(session)
            subtasks = await tm.get_subtasks(parent_task_id)
            
            return [
                {
                    "task_id": t.id,
                    "assigned_agent": t.assigned_agent_id,
                    "status": t.status,
                    "progress_percent": t.progress_percent
                }
                for t in subtasks
            ]


class GetSubtaskResultsTool(BaseTool):
    """Tool for gathering all output results from completed subtasks."""
    
    @property
    def name(self) -> str:
        return "get_subtask_results"
        
    @property
    def description(self) -> str:
        return "Gather aggregated results from all subtasks of a parent task."
    
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "parent_task_id": {
                    "type": "string",
                    "description": "The ID of the parent orchestrator task."
                }
            },
            "required": ["parent_task_id"]
        }
        
    async def execute(self, **kwargs) -> Any:
        parent_task_id = kwargs.get("parent_task_id")
        if not parent_task_id:
            return "Error: missing parent_task_id"
            
        from app.db.engine import get_async_session
        from app.services.task_manager import TaskManager
        
        async with get_async_session() as session:
            tm = TaskManager(session)
            subtasks = await tm.get_subtasks(parent_task_id)
            
            results = {}
            for t in subtasks:
                if t.status == "completed":
                    results[t.assigned_agent_id] = t.result
                elif t.status == "failed":
                    results[t.assigned_agent_id] = f"FAILED: {t.error_message}"
                else:
                    results[t.assigned_agent_id] = f"Still running ({t.progress_percent}%)"
                    
            return results
