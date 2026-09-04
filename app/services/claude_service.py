import json
import os
import re
from typing import Any, Optional, Dict, List
from anthropic import AsyncAnthropic

class ClaudeResponse(str):
    def __new__(cls, content: str, model: str):
        obj = str.__new__(cls, content)
        obj.model = model
        return obj

class ClaudeResponseDict(dict):
    def __init__(self, data: dict, model: str):
        super().__init__(data)
        self.model = model

class ClaudeResponseList(list):
    def __init__(self, data: list, model: str):
        super().__init__(data)
        self.model = model

def _safe_parse_json(content: str, model: str) -> Any:
    # Try parsing directly
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            return ClaudeResponseDict(data, model)
        elif isinstance(data, list):
            return ClaudeResponseList(data, model)
        return data
    except json.JSONDecodeError:
        pass

    # Try cleaning markdown code blocks if present
    try:
        cleaned = content.strip()
        cleaned = re.sub(r"^```json\s*", "", cleaned)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return ClaudeResponseDict(data, model)
        elif isinstance(data, list):
            return ClaudeResponseList(data, model)
        return data
    except Exception:
        # Fallback to returning the raw ClaudeResponse string
        return ClaudeResponse(content, model)

def _prepare_user_content(user_content: Any) -> Any:
    if user_content is None:
        return None
    if isinstance(user_content, dict):
        return json.dumps(user_content, default=str)
    if isinstance(user_content, list):
        # If it's a list of dicts with 'type' key, it's valid Anthropic content blocks format
        if all(isinstance(x, dict) and "type" in x for x in user_content):
            return user_content
        return json.dumps(user_content, default=str)
    if isinstance(user_content, str):
        return user_content
    return str(user_content)


class ClaudeService:
    def __init__(self):
        self.client = AsyncAnthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            default_headers={"anthropic-beta": "prompt-caching-2024-07-31"}
        )
        # Environment-driven routing
        self.text_model = os.getenv("TEXT_MODEL", "claude-opus-4-7")
        self.utility_model = os.getenv("UTILITY_MODEL", "claude-fable-5")
        self.vision_model = os.getenv("VISION_MODEL", "claude-opus-4-7")
        self.vision_fallback_model = os.getenv("VISION_FALLBACK_MODEL")
        self.fable_model = os.getenv("FABLE_MODEL", "claude-fable-5")

    def _format_system_prompt_with_cache(self, system_prompt: str) -> list:
        return [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"}
            }
        ]

    def _apply_dynamic_cache_control(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        import copy
        msgs = copy.deepcopy(messages)
        # Strip existing cache_control markers from all messages/blocks
        for msg in msgs:
            content = msg.get("content")
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and "cache_control" in block:
                        del block["cache_control"]
            elif isinstance(content, dict) and "cache_control" in content:
                del content["cache_control"]

        # Place cache_control: {"type": "ephemeral"} on the LAST content block of the LAST message
        if msgs:
            last_msg = msgs[-1]
            content = last_msg.get("content")
            if isinstance(content, str):
                last_msg["content"] = [
                    {
                        "type": "text",
                        "text": content,
                        "cache_control": {"type": "ephemeral"}
                    }
                ]
            elif isinstance(content, list) and len(content) > 0:
                last_block = content[-1]
                if isinstance(last_block, dict):
                    last_block["cache_control"] = {"type": "ephemeral"}
                elif isinstance(last_block, str):
                    content[-1] = {
                        "type": "text",
                        "text": last_block,
                        "cache_control": {"type": "ephemeral"}
                    }
        return msgs

    async def _create_message_with_fallback(self, params: dict) -> Any:
        try:
            return await self.client.messages.create(**params)
        except Exception as e:
            err_msg = str(e).lower()
            if "temperature" in err_msg and "deprecated" in err_msg and "temperature" in params:
                model = params.get("model")
                print(f"[CLAUDE] Temperature is deprecated for model {model}. Retrying without temperature...")
                params_copy = dict(params)
                del params_copy["temperature"]
                return await self.client.messages.create(**params_copy)
            raise e

    async def json_completion(
        self,
        system_prompt: str,
        user_content: Any = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model_override: Optional[str] = None,
        **kwargs
    ) -> Any:
        model = model_override or kwargs.get("model") or self.text_model
        try:
            print(f"[CLAUDE] json_completion -> model={model}")
            raw_messages = messages if messages is not None else [{"role": "user", "content": _prepare_user_content(user_content)}]
            prepared_messages = self._apply_dynamic_cache_control(raw_messages)
            params = {
                "model": model,
                "max_tokens": max_tokens or 4096,
                "system": self._format_system_prompt_with_cache(system_prompt),
                "messages": prepared_messages
            }
            if temperature is not None:
                params["temperature"] = temperature
                
            response = await self._create_message_with_fallback(params)
            if hasattr(response, "usage"):
                print(f"[CLAUDE USAGE - JSON] Input: {getattr(response.usage, 'input_tokens', 0)}, Output: {getattr(response.usage, 'output_tokens', 0)}, Cache Read: {getattr(response.usage, 'cache_read_input_tokens', 0)}, Cache Write: {getattr(response.usage, 'cache_creation_input_tokens', 0)}")
            content = response.content[0].text
            return _safe_parse_json(content, model)
        except Exception as e:
            print(f"[CLAUDE] Error during json_completion: {str(e)}")
            raise e

    async def vision_json_completion(
        self,
        system_prompt: str,
        user_content: Any = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model_override: Optional[str] = None,
        **kwargs
    ) -> Any:
        model = model_override or self.vision_model
        try:
            print(f"[CLAUDE] vision_json_completion -> model={model}")
            raw_messages = messages if messages is not None else [{"role": "user", "content": _prepare_user_content(user_content)}]
            prepared_messages = self._apply_dynamic_cache_control(raw_messages)
            params = {
                "model": model,
                "max_tokens": max_tokens or 4096,
                "system": self._format_system_prompt_with_cache(system_prompt),
                "messages": prepared_messages
            }
            if temperature is not None:
                params["temperature"] = temperature

            response = await self._create_message_with_fallback(params)
            if hasattr(response, "usage"):
                print(f"[CLAUDE USAGE - VISION] Input: {getattr(response.usage, 'input_tokens', 0)}, Output: {getattr(response.usage, 'output_tokens', 0)}, Cache Read: {getattr(response.usage, 'cache_read_input_tokens', 0)}, Cache Write: {getattr(response.usage, 'cache_creation_input_tokens', 0)}")
            content = response.content[0].text
            return _safe_parse_json(content, model)
        except Exception as e:
            if self.vision_fallback_model:
                fallback = self.vision_fallback_model
                print(f"[CLAUDE] Error with vision_model {model}: {e}. Falling back to {fallback}")
                try:
                    params["model"] = fallback
                    response = await self._create_message_with_fallback(params)
                    if hasattr(response, "usage"):
                        print(f"[CLAUDE USAGE - VISION FALLBACK] Input: {getattr(response.usage, 'input_tokens', 0)}, Output: {getattr(response.usage, 'output_tokens', 0)}, Cache Read: {getattr(response.usage, 'cache_read_input_tokens', 0)}, Cache Write: {getattr(response.usage, 'cache_creation_input_tokens', 0)}")
                    content = response.content[0].text
                    return _safe_parse_json(content, fallback)
                except Exception as fallback_err:
                    print(f"[CLAUDE] Error during vision fallback: {str(fallback_err)}")
                    raise fallback_err
            else:
                print(f"[CLAUDE] Error during vision_json_completion: {str(e)}")
                raise e

    async def chat_completion(
        self,
        system_prompt: str,
        user_content: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model_override: Optional[str] = None,
        **kwargs
    ) -> str:
        model = model_override or kwargs.get("model") or self.text_model
        try:
            print(f"[CLAUDE] chat_completion -> model={model}")
            raw_messages = messages if messages is not None else [{"role": "user", "content": _prepare_user_content(user_content)}]
            prepared_messages = self._apply_dynamic_cache_control(raw_messages)
            params = {
                "model": model,
                "max_tokens": max_tokens or 4096,
                "system": self._format_system_prompt_with_cache(system_prompt),
                "messages": prepared_messages
            }
            if temperature is not None:
                params["temperature"] = temperature

            response = await self._create_message_with_fallback(params)
            if hasattr(response, "usage"):
                print(f"[CLAUDE USAGE - CHAT] Input: {getattr(response.usage, 'input_tokens', 0)}, Output: {getattr(response.usage, 'output_tokens', 0)}, Cache Read: {getattr(response.usage, 'cache_read_input_tokens', 0)}, Cache Write: {getattr(response.usage, 'cache_creation_input_tokens', 0)}")
            return ClaudeResponse(response.content[0].text, model)
        except Exception as e:
            print(f"[CLAUDE] Error during chat_completion: {str(e)}")
            raise e

    async def text_completion(
        self,
        system_prompt: str,
        user_content: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        res = await self.chat_completion(
            system_prompt=system_prompt,
            user_content=user_content,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        return str(res)

    async def tool_runner(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools: List[Any],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model_override: Optional[str] = None,
        **kwargs
    ) -> Any:
        import copy
        import inspect

        from app.tools.calculator_tool import calculator_tool

        model = model_override or self.text_model
        print(f"[CLAUDE] tool_runner (dynamic caching enabled) -> model={model}")

        # Ensure calculator tool is always available for deterministic math
        has_calc = any(
            (isinstance(t, dict) and t.get("name") in ("calculate", "calculator")) or
            (hasattr(t, "name") and getattr(t, "name") in ("calculate", "calculator"))
            for t in (tools or [])
        )
        effective_tools = list(tools or [])
        if not has_calc:
            effective_tools.append(calculator_tool)

        # Map tools by name for execution during tool loop turns
        tool_map = {}
        formatted_tools = []
        for t in effective_tools:
            # Step 1: Extract API-compatible dictionary parameter for tool registration
            if isinstance(t, dict):
                param = t
            elif hasattr(t, "to_param") and callable(getattr(t, "to_param")):
                param = t.to_param()
            elif hasattr(t, "to_dict") and callable(getattr(t, "to_dict")):
                param = t.to_dict()
            elif hasattr(t, "dict") and callable(getattr(t, "dict")):
                param = t.dict()
            elif hasattr(t, "model_dump") and callable(getattr(t, "model_dump")):
                param = t.model_dump()
            else:
                param = t

            formatted_tools.append(param)

            # Step 2: Index executable tool object in tool_map by name
            tool_name = None
            if hasattr(t, "name") and isinstance(getattr(t, "name"), str):
                tool_name = getattr(t, "name")
            elif isinstance(param, dict) and "name" in param and isinstance(param["name"], str):
                tool_name = param["name"]
            elif hasattr(t, "__name__") and isinstance(getattr(t, "__name__"), str):
                tool_name = getattr(t, "__name__")

            if tool_name:
                tool_map[tool_name] = t

        working_messages = copy.deepcopy(messages)
        step = 0
        max_steps = 15

        try:
            while step < max_steps:
                step += 1

                # Dynamically apply cache_control to the newest message block on each iteration
                prepared_messages = self._apply_dynamic_cache_control(working_messages)

                params = {
                    "model": model,
                    "max_tokens": max_tokens or 4096,
                    "system": self._format_system_prompt_with_cache(system_prompt),
                    "messages": prepared_messages,
                    "tools": formatted_tools,
                }
                if temperature is not None:
                    params["temperature"] = temperature

                response = await self._create_message_with_fallback(params)

                # Print token usage logs for EVERY step in the run
                if hasattr(response, "usage"):
                    usage = response.usage
                    in_tok = getattr(usage, "input_tokens", 0)
                    out_tok = getattr(usage, "output_tokens", 0)
                    c_read = getattr(usage, "cache_read_input_tokens", 0)
                    c_write = getattr(usage, "cache_creation_input_tokens", 0)
                    print(f"[CLAUDE USAGE - TOOL LOOP STEP {step}] Input: {in_tok}, Output: {out_tok}, Cache Read: {c_read}, Cache Write: {c_write}")

                if response.stop_reason != "tool_use":
                    return response

                # Handle tool execution
                assistant_blocks = []
                tool_calls = []
                for block in response.content:
                    if block.type == "text":
                        assistant_blocks.append({"type": "text", "text": block.text})
                    elif block.type == "tool_use":
                        assistant_blocks.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input
                        })
                        tool_calls.append(block)

                working_messages.append({
                    "role": "assistant",
                    "content": assistant_blocks
                })

                tool_result_blocks = []
                for t_call in tool_calls:
                    t_name = t_call.name
                    t_input = t_call.input if isinstance(t_call.input, dict) else {}
                    t_id = t_call.id

                    print(f"[CLAUDE TOOL EXECUTION Step {step}] Executing tool '{t_name}' with args: {t_input}")
                    tool_output_str = ""
                    try:
                        # Resilient tool lookup (exact -> lowercase -> normalized match)
                        tool_obj = tool_map.get(t_name)
                        if not tool_obj:
                            clean_t_name = t_name.lower().replace("_", "").replace("-", "")
                            for k, v in tool_map.items():
                                clean_k = str(k).lower().replace("_", "").replace("-", "")
                                if clean_k == clean_t_name or clean_k in clean_t_name or clean_t_name in clean_k:
                                    tool_obj = v
                                    break

                        if tool_obj:
                            # 1. BetaAsyncFunctionTool / functions wrapping .func
                            if hasattr(tool_obj, "func") and callable(getattr(tool_obj, "func")):
                                res = tool_obj.func(**t_input)
                                if inspect.isawaitable(res):
                                    res = await res
                                tool_output_str = json.dumps(res, default=str) if isinstance(res, (dict, list)) else str(res)
                            # 2. Memory tools (LightSignalAsyncMemoryTool / LightSignalMemoryTool)
                            elif hasattr(tool_obj, "view") or "memory" in t_name.lower():
                                cmd_name = t_input.get("command", "view") if isinstance(t_input, dict) else "view"
                                if not hasattr(tool_obj, cmd_name):
                                    raise AttributeError(f"Memory tool does not support command '{cmd_name}'")
                                method = getattr(tool_obj, cmd_name)
                                from anthropic.types.beta import (
                                    BetaMemoryTool20250818ViewCommand,
                                    BetaMemoryTool20250818CreateCommand,
                                    BetaMemoryTool20250818StrReplaceCommand,
                                    BetaMemoryTool20250818InsertCommand,
                                    BetaMemoryTool20250818DeleteCommand,
                                    BetaMemoryTool20250818RenameCommand,
                                )
                                if cmd_name == "view":
                                    cmd = BetaMemoryTool20250818ViewCommand(command="view", path=t_input.get("path", "/memories"), view_range=t_input.get("view_range"))
                                elif cmd_name == "create":
                                    cmd = BetaMemoryTool20250818CreateCommand(command="create", path=t_input.get("path", ""), file_text=t_input.get("file_text", t_input.get("content", "")))
                                elif cmd_name == "str_replace":
                                    cmd = BetaMemoryTool20250818StrReplaceCommand(command="str_replace", path=t_input.get("path", ""), old_str=t_input.get("old_str", ""), new_str=t_input.get("new_str", ""))
                                elif cmd_name == "insert":
                                    cmd = BetaMemoryTool20250818InsertCommand(command="insert", path=t_input.get("path", ""), insert_line=t_input.get("insert_line", 0), new_str=t_input.get("new_str", ""))
                                elif cmd_name == "delete":
                                    cmd = BetaMemoryTool20250818DeleteCommand(command="delete", path=t_input.get("path", ""))
                                elif cmd_name == "rename":
                                    cmd = BetaMemoryTool20250818RenameCommand(command="rename", old_path=t_input.get("old_path", ""), new_path=t_input.get("new_path", ""))
                                else:
                                    cmd = t_input
                                res = method(cmd)
                                if inspect.isawaitable(res):
                                    res = await res
                                tool_output_str = json.dumps(res, default=str) if isinstance(res, (dict, list)) else str(res)
                            # 3. Direct execute / run / call
                            elif hasattr(tool_obj, "execute") and callable(getattr(tool_obj, "execute")):
                                res = tool_obj.execute(**t_input)
                                if inspect.isawaitable(res):
                                    res = await res
                                tool_output_str = json.dumps(res, default=str) if isinstance(res, (dict, list)) else str(res)
                            elif hasattr(tool_obj, "run") and callable(getattr(tool_obj, "run")):
                                res = tool_obj.run(**t_input)
                                if inspect.isawaitable(res):
                                    res = await res
                                tool_output_str = json.dumps(res, default=str) if isinstance(res, (dict, list)) else str(res)
                            elif hasattr(tool_obj, "call") and callable(getattr(tool_obj, "call")):
                                try:
                                    res = tool_obj.call(**t_input)
                                except TypeError:
                                    res = tool_obj(**t_input)
                                if inspect.isawaitable(res):
                                    res = await res
                                tool_output_str = json.dumps(res, default=str) if isinstance(res, (dict, list)) else str(res)
                            elif callable(tool_obj):
                                res = tool_obj(**t_input)
                                if inspect.isawaitable(res):
                                    res = await res
                                tool_output_str = json.dumps(res, default=str) if isinstance(res, (dict, list)) else str(res)
                            else:
                                tool_output_str = f"Tool '{t_name}' executed."
                        else:
                            tool_output_str = f"Error: Tool '{t_name}' not found in tool_map."
                    except Exception as tool_err:
                        print(f"[CLAUDE TOOL ERROR] Error executing tool '{t_name}': {tool_err}")
                        tool_output_str = f"Error executing tool '{t_name}': {str(tool_err)}"

                    tool_result_blocks.append({
                        "type": "tool_result",
                        "tool_use_id": t_id,
                        "content": tool_output_str
                    })

                working_messages.append({
                    "role": "user",
                    "content": tool_result_blocks
                })

            return response
        except Exception as e:
            print(f"[CLAUDE] Error during tool_runner: {str(e)}")
            raise e

claude_service = ClaudeService()