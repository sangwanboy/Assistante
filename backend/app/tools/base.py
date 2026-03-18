from abc import ABC, abstractmethod


class BaseTool(ABC):
    contract_version: str = "1.0"

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

    @property
    def category(self) -> str:
        return "general"

    @property
    def risk_level(self) -> str:
        return "medium"

    @property
    def allowed_modes(self) -> list[str]:
        return ["manual", "autonomous"]

    @property
    def requires_approval(self) -> bool:
        return False
