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
        return json.dumps(user_content)
    if isinstance(user_content, list):
        # If it's a list of dicts with 'type' key, it's valid Anthropic content blocks format
        if all(isinstance(x, dict) and "type" in x for x in user_content):
            return user_content
        return json.dumps(user_content)
    if isinstance(user_content, str):
        return user_content
    return str(user_content)


class ClaudeService:
    def __init__(self):
        self.client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        # Environment-driven routing
        self.text_model = os.getenv("TEXT_MODEL", "claude-opus-4-7")
        self.vision_model = os.getenv("VISION_MODEL", "claude-opus-4-7")
        self.vision_fallback_model = os.getenv("VISION_FALLBACK_MODEL")

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
        **kwargs
    ) -> Any:
        model = self.text_model
        try:
            print(f"[CLAUDE] json_completion -> model={model}")
            params = {
                "model": model,
                "max_tokens": max_tokens or 4096,
                "system": system_prompt,
                "messages": messages if messages is not None else [{"role": "user", "content": _prepare_user_content(user_content)}]
            }
            if temperature is not None:
                params["temperature"] = temperature
                
            response = await self._create_message_with_fallback(params)
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
        **kwargs
    ) -> Any:
        model = self.vision_model
        try:
            print(f"[CLAUDE] vision_json_completion -> model={model}")
            params = {
                "model": model,
                "max_tokens": max_tokens or 4096,
                "system": system_prompt,
                "messages": messages if messages is not None else [{"role": "user", "content": _prepare_user_content(user_content)}]
            }
            if temperature is not None:
                params["temperature"] = temperature

            response = await self._create_message_with_fallback(params)
            content = response.content[0].text
            return _safe_parse_json(content, model)
        except Exception as e:
            if self.vision_fallback_model:
                fallback = self.vision_fallback_model
                print(f"[CLAUDE] Error with vision_model {model}: {e}. Falling back to {fallback}")
                try:
                    params["model"] = fallback
                    response = await self._create_message_with_fallback(params)
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
        **kwargs
    ) -> str:
        model = self.text_model
        try:
            print(f"[CLAUDE] chat_completion -> model={model}")
            params = {
                "model": model,
                "max_tokens": max_tokens or 4096,
                "system": system_prompt,
                "messages": messages if messages is not None else [{"role": "user", "content": _prepare_user_content(user_content)}]
            }
            if temperature is not None:
                params["temperature"] = temperature

            response = await self._create_message_with_fallback(params)
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
        **kwargs
    ) -> Any:
        model = self.text_model
        try:
            print(f"[CLAUDE] tool_runner -> model={model}")
            params = {
                "model": model,
                "max_tokens": max_tokens or 4096,
                "system": system_prompt,
                "messages": messages,
                "tools": tools,
            }
            if temperature is not None:
                params["temperature"] = temperature

            # Call client.beta.messages.tool_runner
            runner = self.client.beta.messages.tool_runner(**params)
            response = await runner.until_done()
            return response
        except Exception as e:
            err_msg = str(e).lower()
            if "temperature" in err_msg and "deprecated" in err_msg and temperature is not None:
                print(f"[CLAUDE] Temperature is deprecated for model {model} in tool_runner. Retrying without temperature...")
                params_copy = dict(params)
                if "temperature" in params_copy:
                    del params_copy["temperature"]
                try:
                    runner = self.client.beta.messages.tool_runner(**params_copy)
                    response = await runner.until_done()
                    return response
                except Exception as retry_err:
                    print(f"[CLAUDE] Error during tool_runner retry: {str(retry_err)}")
                    raise retry_err
            print(f"[CLAUDE] Error during tool_runner: {str(e)}")
            raise e

claude_service = ClaudeService()