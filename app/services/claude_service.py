import os
from typing import Any, Optional
from anthropic import AsyncAnthropic

class ClaudeResponse(str):
    def __new__(cls, content: str, model: str):
        obj = str.__new__(cls, content)
        obj.model = model
        return obj

class ClaudeService:
    def __init__(self):
        self.client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        # Environment-driven routing
        self.text_model = os.getenv("TEXT_MODEL", "claude-opus-4-7")
        self.vision_model = os.getenv("VISION_MODEL", "claude-opus-4-7")
        self.vision_fallback_model = os.getenv("VISION_FALLBACK_MODEL")

    async def json_completion(self, system_prompt: str, user_content: Any) -> Any:
        model = self.text_model
        try:
            print(f"[CLAUDE] json_completion -> model={model}")
            response = await self.client.messages.create(
                model=model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}]
            )
            return ClaudeResponse(response.content[0].text, model)
        except Exception as e:
            print(f"[CLAUDE] Error during json_completion: {str(e)}")
            raise e

    async def vision_json_completion(self, system_prompt: str, user_content: Any) -> Any:
        model = self.vision_model
        try:
            print(f"[CLAUDE] vision_json_completion -> model={model}")
            response = await self.client.messages.create(
                model=model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}]
            )
            return ClaudeResponse(response.content[0].text, model)
        except Exception as e:
            if self.vision_fallback_model:
                fallback = self.vision_fallback_model
                print(f"[CLAUDE] Error with vision_model {model}: {e}. Falling back to {fallback}")
                try:
                    response = await self.client.messages.create(
                        model=fallback,
                        max_tokens=4096,
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_content}]
                    )
                    return ClaudeResponse(response.content[0].text, fallback)
                except Exception as fallback_err:
                    print(f"[CLAUDE] Error during vision fallback: {str(fallback_err)}")
                    raise fallback_err
            else:
                print(f"[CLAUDE] Error during vision_json_completion: {str(e)}")
                raise e

    async def chat_completion(self, system_prompt: str, user_content: str) -> str:
        model = self.text_model
        try:
            print(f"[CLAUDE] chat_completion -> model={model}")
            response = await self.client.messages.create(
                model=model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}]
            )
            return ClaudeResponse(response.content[0].text, model)
        except Exception as e:
            print(f"[CLAUDE] Error during chat_completion: {str(e)}")
            raise e

claude_service = ClaudeService()