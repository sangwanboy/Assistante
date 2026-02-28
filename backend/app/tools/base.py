from abc import ABC, abstractmethod


class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @abstractmethod
    def parameters_schema(self) -> dict:
        """Return JSON Schema dict describing this tool's parameters."""
        ...

    @abstractmethod
    async def execute(self, **params) -> str:
        """Execute the tool with the given parameters. Returns a string result."""
        ...
