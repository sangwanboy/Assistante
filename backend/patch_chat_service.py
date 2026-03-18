import re

with open("app/services/chat_service.py", "r", encoding="utf-8") as f:
    code = f.read()

# I need to find `async def _execute_tool_calls`
old_method_pattern = r'    async def _execute_tool_calls\([^:]+:\n        """Execute tool calls.*?return results'

new_method = """    async def _execute_single_tool_call(
        self,
        tc: dict,
        conversation_id: str,
        agent_id: str = None,
        task_id: str = None,
    ) -> list:
        import inspect
        import traceback
        import asyncio
        from app.services.hitl_manager import HITLManager
        from app.providers.base import ChatMessage

        hitl_manager = HITLManager.get_instance()
        tc_id = str(tc.get("id") or "").strip()
        if not tc_id:
            return None

        func = tc.get("function", {})
        tool_name = func.get("name", "")
        args_str = func.get("arguments", "{}")

        try:
            args = json.loads(args_str) if isinstance(args_str, str) else args_str
        except json.JSONDecodeError:
            args = {}

        # -- HITL Check for sensitive tools --
        sensitive_tools = ["command_executor"]
        if tool_name in sensitive_tools:
            try:
                approved = await hitl_manager.request_approval(tc_id, tool_name, args)
            except Exception:
                approved = False  # Auto-deny if HITL service is unreachable

            if not approved:
                return ChatMessage(
                    role="tool",
                    content="Execution denied by user via HITL.",
                    tool_call_id=tc_id
                )

        images = None
        try:
            tool = self.tools.get(tool_name)

            # -- Context Injection Logic --
            sig = inspect.signature(tool.execute)
            params = sig.parameters
            has_var_keyword = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())

            extra_kwargs = {}
            context_map = {
                "conversation_id": conversation_id,
                "_session": self.session,
                "agent_id": agent_id,
                "_agent_id": agent_id,
                "task_id": task_id,
                "_task_id": task_id,
            }

            for param_name, value in context_map.items():
                if param_name in params or has_var_keyword:
                    extra_kwargs[param_name] = value

            exec_kwargs = {**extra_kwargs, **args}

            # -- Execution with Timeout --
            result_raw = await asyncio.wait_for(
                tool.execute(**exec_kwargs),
                timeout=180.0
            )
            result_str = str(result_raw)

            # -- Visual Content Extraction (Phase 6) --
            try:
                parsed_result = json.loads(result_str)
                if isinstance(parsed_result, dict) and "image_base64" in parsed_result:
                    images = [parsed_result.pop("image_base64")]
                    result_str = json.dumps(parsed_result)
            except (json.JSONDecodeError, TypeError):
                pass

        except asyncio.TimeoutError:
            result_str = f"Tool '{tool_name}' timed out after 180 seconds."
        except Exception as e:
            error_trace = traceback.format_exc()
            result_str = (
                f"Tool '{tool_name}' failed with error: {str(e)}\n\n"
                f"Traceback:\n{error_trace}"
            )

        return ChatMessage(
            role="tool",
            content=result_str,
            tool_call_id=tc_id,
            images=images,
        )

    async def _execute_tool_calls(
        self,
        tool_calls: list[dict],
        conversation_id: str,
        agent_id: str = None,
        task_id: str = None,
    ) -> list:
        \"\"\"Execute tool calls and return tool result messages concurrently.\"\"\"
        import asyncio
        from app.providers.base import ChatMessage
        
        tasks = [
            self._execute_single_tool_call(tc, conversation_id, agent_id, task_id)
            for tc in tool_calls
        ]
        
        import logging
        logger = logging.getLogger(__name__)

        raw_results = await asyncio.gather(*tasks, return_exceptions=True)
        results = []
        for r in raw_results:
            if isinstance(r, Exception):
                logger.error("Exception in concurrent tool execution", exc_info=r)
            elif isinstance(r, ChatMessage):
                results.append(r)
        
        return results"""

code_new = re.sub(old_method_pattern, new_method, code, flags=re.DOTALL)

with open("app/services/chat_service.py", "w", encoding="utf-8") as f:
    f.write(code_new)

print("Patched!")
