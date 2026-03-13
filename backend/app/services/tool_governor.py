import json
import hashlib
import time
from typing import Any


class ToolGovernor:
    """Tracks and limits repetitive tool usage within a single agent task loop."""
    
    def __init__(self, max_consecutive: int = 3, reflection_interval: int = 3):
        self.tool_usage: dict[str, int] = {}
        self.call_history: list[dict[str, Any]] = []
        self.step_count = 0
        self.max_consecutive = max_consecutive
        self.reflection_interval = reflection_interval
        self._last_tool_name = None
        self._consecutive_count = 0
        self._recursion_depth = 0
        self._max_recursion_depth = 3
        self._tool_timestamps: dict[str, list[float]] = {}  # tool_name -> list of timestamps
        self._per_tool_rpm = 5  # max calls per minute per tool

    def _hash_args(self, args: dict | str) -> str:
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                pass
        if isinstance(args, dict):
            # Sort keys for consistent hashing
            args_str = json.dumps(args, sort_keys=True)
            return hashlib.md5(args_str.encode()).hexdigest()
        return str(args)

    def record_and_check(self, tool_name: str, tool_args: dict | str) -> str | None:
        """Records a tool call and returns an intervention prompt if the agent is stuck."""
        self.step_count += 1
        self.tool_usage[tool_name] = self.tool_usage.get(tool_name, 0) + 1
        
        args_hash = self._hash_args(tool_args)
        
        # Check strict repetition (exact same tool + args)
        if self.call_history:
            last_call = self.call_history[-1]
            if last_call["name"] == tool_name and last_call["hash"] == args_hash:
                # Agent is repeating the exact same failed action!
                self.call_history.append({"name": tool_name, "hash": args_hash})
                return (
                    f"🛑 GOVERNOR INTERVENTION: You just called `{tool_name}` with the EXACT SAME arguments "
                    f"that you tried previously! This is an infinite loop. "
                    f"You MUST STOP, reflect on why it failed, and try a completely different approach or tool."
                )
                
        # Check consecutive tool calls regardless of args
        if tool_name == self._last_tool_name:
            self._consecutive_count += 1
        else:
            self._last_tool_name = tool_name
            self._consecutive_count = 1
            
        self.call_history.append({"name": tool_name, "hash": args_hash})

        if self._consecutive_count > self.max_consecutive:
            return (
                f"🛑 GOVERNOR INTERVENTION: You have called `{tool_name}` {self._consecutive_count} times in a row. "
                f"You are fixated on this tool. Please fallback to another tool or conclude your execution."
            )
            
        return None
        
    def should_reflect(self) -> str | None:
        """Injects a self-correction reflection step every N steps."""
        if self.step_count > 0 and self.step_count % self.reflection_interval == 0:
            history_str = ", ".join([h["name"] for h in self.call_history[-self.reflection_interval:]])
            return (
                f"💡 REFLECTION STEP: You are executing a task. Steps taken so far: {self.step_count}. "
                f"Recent tools used: [{history_str}].\n"
                f"Have you made meaningful progress? If not, propose a different approach before calling tools again."
            )
        return None

    def check_before_execution(self, tool_name: str, agent_id: str = "") -> str | None:
        """Pre-execution check: recursion depth, per-tool rate limits."""
        # Recursion protection
        if self._recursion_depth > self._max_recursion_depth:
            return (
                f"GOVERNOR HALT: Tool recursion depth exceeded ({self._recursion_depth}/{self._max_recursion_depth}). "
                f"Tool chains are too deep. Provide your final answer now."
            )

        # Per-tool rate limit (5 calls/minute per tool)
        now = time.time()
        if tool_name not in self._tool_timestamps:
            self._tool_timestamps[tool_name] = []

        # Clean old timestamps (older than 60s)
        self._tool_timestamps[tool_name] = [
            ts for ts in self._tool_timestamps[tool_name] if now - ts < 60
        ]

        if len(self._tool_timestamps[tool_name]) >= self._per_tool_rpm:
            return (
                f"GOVERNOR RATE LIMIT: Tool '{tool_name}' has been called {self._per_tool_rpm} times "
                f"in the last minute. Wait before calling it again, or use a different approach."
            )

        self._tool_timestamps[tool_name].append(now)
        return None

    def enter_tool_chain(self):
        """Called when a tool invokes another tool (recursion tracking)."""
        self._recursion_depth += 1

    def exit_tool_chain(self):
        """Called when a tool chain completes."""
        self._recursion_depth = max(0, self._recursion_depth - 1)
