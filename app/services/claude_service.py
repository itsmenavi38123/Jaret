import json
import os
from typing import Any, Dict, Optional
from anthropic import AsyncAnthropic, APIStatusError, NotFoundError, PermissionDeniedError

# Errors that mean "this model is currently unavailable to us" -- worth
# auto-falling-back on. We deliberately do NOT fall back on things like
# bad-request/validation errors, since retrying those on a different model
# would just hide a real bug.
FABLE_UNAVAILABLE_ERRORS = (NotFoundError, PermissionDeniedError)


class ClaudeService:
    def __init__(self):
        self.client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        # Text-path / default model (Opus or Sonnet -- whatever is configured).
        self.model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

# Vision-path models. FABLE_ENABLED is the single "easy to change" switch:
        # flip it to false in .env to force everyone to Opus-vision regardless of
        # whether Fable is actually reachable (e.g. if Fable comes back but you
        # want to stay off it for cost reasons). Leave it true (default) and the
        # service will keep trying Fable first and silently falling back to Opus
        # for as long as Fable keeps failing -- no code change needed when Fable
        # is unbanned, it will just start succeeding again on its own.
        self.fable_enabled = os.getenv("FABLE_ENABLED", "true").lower() in ("1", "true", "yes")
        self.fable_model = os.getenv("FABLE_MODEL", "claude-fable-5")
        self.vision_fallback_model = os.getenv("VISION_FALLBACK_MODEL", "claude-opus-4-7")

    async def json_completion(self, system_prompt: str, user_content: Any) -> Any:
        """Text-path completion (txt/md/xlsx/csv) -- always uses self.model."""
        try:
            print(f"[CLAUDE] json_completion -> model={self.model}")
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}]
            )
            return response.content[0].text
        except Exception as e:
            print(f"[CLAUDE] Error during json_completion: {str(e)}")
            raise e

    async def vision_json_completion(self, system_prompt: str, user_content: Any) -> Any:
        """
        Vision-path completion (pdf/image/converted-office-doc).

        Tries Fable first (if enabled). If Fable is unavailable for any reason
        (suspended, retired, no access, etc.) it automatically retries the exact
        same request on the Opus vision fallback model -- no manual step. This
        means the moment Fable access is restored, calls just start succeeding
        on Fable again with zero code changes.
        """
        if self.fable_enabled:
            try:
                print(f"[CLAUDE] vision_json_completion -> trying model={self.fable_model}")
                response = await self.client.messages.create(
                    model=self.fable_model,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_content}]
                )
                return response.content[0].text
            except FABLE_UNAVAILABLE_ERRORS as e:
                print(f"[CLAUDE] Fable unavailable ({type(e).__name__}: {e}). Falling back to {self.vision_fallback_model}.")
            except APIStatusError as e:
                # Defensive: some "model not found"/"access revoked" cases may
                # surface as a generic APIStatusError with status 404/403
                # depending on SDK version. Treat those the same way.
                if e.status_code in (403, 404):
                    print(f"[CLAUDE] Fable unavailable (status {e.status_code}). Falling back to {self.vision_fallback_model}.")
                else:
                    raise
        else:
            print(f"[CLAUDE] FABLE_ENABLED=false -> skipping Fable, using {self.vision_fallback_model}")

        try:
            print(f"[CLAUDE] vision_json_completion -> model={self.vision_fallback_model}")
            response = await self.client.messages.create(
                model=self.vision_fallback_model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}]
            )
            return response.content[0].text
        except Exception as e:
            print(f"[CLAUDE] Error during vision_json_completion fallback: {str(e)}")
            raise e

    async def chat_completion(self, system_prompt: str, user_content: str) -> str:
        try:
            print(f"[CLAUDE] chat_completion -> model={self.model}")
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}]
            )
            return response.content[0].text
        except Exception as e:
            print(f"[CLAUDE] Error during chat_completion: {str(e)}")
            raise e

claude_service = ClaudeService()