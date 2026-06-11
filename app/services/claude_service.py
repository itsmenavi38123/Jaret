import json
import os
from typing import Any, Dict, List

from anthropic import AsyncAnthropic


class ClaudeService:

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")

        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found")

        self.client = AsyncAnthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"

    async def json_completion(
        self,
        *,
        system_prompt: str,
        user_content: Any,
        temperature: float = 0.2,
        max_tokens: int = 4000,
    ) -> Dict[str, Any]:
        
        print(f"[CLAUDE] json_completion -> model={self.model}")
        if not isinstance(user_content, str):
            user_content = json.dumps(user_content, default=str)

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_content,
                }
            ],
        )

        content = self._extract_text(response)

        return self._safe_parse_json(content)

    async def text_completion(
        self,
        *,
        system_prompt: str,
        user_content: Any,
        temperature: float = 0.2,
        max_tokens: int = 4000,
    ) -> str:

        if not isinstance(user_content, str):
            user_content = json.dumps(user_content, default=str)

        print(f"[CLAUDE] json_completion -> model={self.model}")
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_content,
                }
            ],
        )

        return self._extract_text(response).strip()

    async def chat_completion(
        self,
        *,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int = 4000,
    ) -> str:

        claude_messages = []

        for msg in messages:

            role = msg.get("role")

            if role not in ["user", "assistant"]:
                continue

            content = msg.get("content", "")

            if not isinstance(content, str):
                content = json.dumps(content, default=str)

            claude_messages.append(
                {
                    "role": role,
                    "content": content,
                }
            )
        print(f"[CLAUDE] chat_completion -> model={self.model}")
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=claude_messages,
        )

        return self._extract_text(response).strip()

    async def tool_runner(
        self,
        *,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools: List[Any],
        temperature: float = 0.2,
        max_tokens: int = 8000,
    ):

        runner = self.client.beta.messages.tool_runner(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=messages,
            tools=tools,
        )

        return runner.until_done()

    def _extract_text(self, response) -> str:

        content = ""

        for block in response.content:
            if getattr(block, "type", None) == "text":
                content += block.text

        return content

    def _safe_parse_json(self, content: str) -> Dict[str, Any]:

        try:
            return json.loads(content)

        except Exception:

            cleaned = (
                content.replace("```json", "")
                .replace("```", "")
                .strip()
            )

            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1

            if start != -1 and end != -1:
                cleaned = cleaned[start:end]

            return json.loads(cleaned)


claude_service = ClaudeService()