from app.tools.base import BaseTool


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._builtin_names: set[str] = set()

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool

    def unregister(self, name: str):
        """Remove a tool from the registry (only non-builtin tools)."""
        if name in self._tools and name not in self._builtin_names:
            del self._tools[name]

    def get(self, name: str) -> BaseTool:
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found. Available: {list(self._tools.keys())}")
        return tool

    def list_tools(self) -> list[dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters_schema(),
                "is_builtin": t.name in self._builtin_names,
            }
            for t in self._tools.values()
        ]

    def as_provider_format(self) -> list[dict]:
        """Convert all tools to the format expected by LLM providers."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters_schema(),
            }
            for t in self._tools.values()
        ]

    def register_defaults(self, provider_registry=None, session_factory=None):
        """Register all built-in tools."""
        from app.tools.web_search import WebSearchTool
        from app.tools.file_manager import FileManagerTool
        from app.tools.code_executor import CodeExecutorTool
        from app.tools.command_executor import CommandExecutorTool
        from app.tools.datetime_tool import DateTimeTool
        from app.tools.knowledge_base_tool import KnowledgeBaseTool
        from app.tools.tool_creator import ToolCreatorTool
        from app.tools.skill_creator import SkillCreatorTool
        from app.tools.agent_manager import AgentManagerTool
        from app.tools.agent_delegate import AgentDelegationTool
        from app.tools.model_manager import ModelManagerTool
        from app.tools.workflow_manager import WorkflowManagerTool
        from app.tools.browser_tool import BrowserTool
        from app.tools.docker_executor import DockerCodeExecutorTool
        from app.tools.agent_messenger import AgentMessengerTool
        from app.tools.memory_tool import SaveMemoryTool, RecallMemoriesTool, WriteDailyLogTool

        for tool in [
            WebSearchTool(), FileManagerTool(), CodeExecutorTool(), CommandExecutorTool(),
            DateTimeTool(), KnowledgeBaseTool(),
            ToolCreatorTool(), SkillCreatorTool(),
            AgentManagerTool(),
            AgentDelegationTool(
                provider_registry=provider_registry,
                tool_registry=self,
            ),
            ModelManagerTool(),
            WorkflowManagerTool(),
            BrowserTool(),
            DockerCodeExecutorTool(),
            AgentMessengerTool(session_factory=session_factory),
            SaveMemoryTool(),
            RecallMemoriesTool(),
            WriteDailyLogTool(),
        ]:
            self.register(tool)
            self._builtin_names.add(tool.name)

    async def load_custom_tools(self, session):
        """Load all active custom tools from DB and register them."""
        from app.services.custom_tool_service import CustomToolService, DynamicTool

        svc = CustomToolService(session)
        custom_tools = await svc.get_active_tools()
        for ct in custom_tools:
            self.register(DynamicTool(ct))
