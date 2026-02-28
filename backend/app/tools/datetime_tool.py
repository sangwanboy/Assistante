from datetime import datetime, timezone
from app.tools.base import BaseTool


class DateTimeTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_datetime"

    @property
    def description(self) -> str:
        return "Get the current date and time. Useful when the user asks about the current time or date."

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {},
        }

    async def execute(self, **kwargs) -> str:
        now = datetime.now()
        utc = datetime.now(timezone.utc)
        return f"Local: {now.strftime('%Y-%m-%d %H:%M:%S')}\nUTC: {utc.strftime('%Y-%m-%d %H:%M:%S')}"
