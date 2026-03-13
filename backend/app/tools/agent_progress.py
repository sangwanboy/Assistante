from typing import Any, Dict
from app.tools.base import BaseTool

class UpdateTaskProgressTool(BaseTool):
    """Tool for agents to update their current task progress percentage."""
    
    @property
    def name(self) -> str:
        return "update_task_progress"
        
    @property
    def description(self) -> str:
        return "Update the completion percentage of your currently assigned task."
    
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The ID of the task you are currently working on."
                },
                "percent_complete": {
                    "type": "integer",
                    "description": "Estimated completion percentage (0-100)."
                }
            },
            "required": ["task_id", "percent_complete"]
        }
        
    async def execute(self, **kwargs) -> Any:
        task_id = kwargs.get("task_id")
        percent = kwargs.get("percent_complete")
        
        if not task_id or percent is None:
            return "Error: task_id and percent_complete are required."
            
        try:
            percent = int(percent)
        except ValueError:
            return "Error: percent_complete must be an integer."
            
        from app.db.engine import get_async_session
        from app.services.task_manager import TaskManager
        
        async with get_async_session() as session:
            tm = TaskManager(session)
            t = await tm.update_progress(task_id, percent)
            if not t:
                return f"Error: task {task_id} not found."
                
            return f"Progress successfully updated to {t.progress_percent}%."
