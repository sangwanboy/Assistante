from app.tools.base import BaseTool


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found. Available: {list(self._tools.keys())}")
        return tool

    def list_tools(self) -> list[dict]:
        return [
            {"name": t.name, "description": t.description, "parameters": t.parameters_schema()}
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

    def register_defaults(self):
        """Register all built-in tools."""
        from app.tools.web_search import WebSearchTool
        from app.tools.file_manager import FileManagerTool
        from app.tools.code_executor import CodeExecutorTool
        from app.tools.datetime_tool import DateTimeTool
        from app.tools.knowledge_base_tool import KnowledgeBaseTool

        self.register(WebSearchTool())
        self.register(FileManagerTool())
        self.register(CodeExecutorTool())
        self.register(DateTimeTool())
        self.register(KnowledgeBaseTool())
