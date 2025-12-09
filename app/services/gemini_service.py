"""
Gemini Service
Thin wrapper around Gemini 3 APIs with JSON-structured prompts.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import httpx


class GeminiService:
    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        self.base_url = os.getenv(
            "GEMINI_API_BASE_URL",
            "https://generativelanguage.googleapis.com/v1beta/models",
        )
        # Default to a recent generateContent-capable model; override via env if needed.
        self.dashboard_model = os.getenv("GEMINI_DASHBOARD_MODEL", "gemini-2.5-flash")
        self.ai_health_model = os.getenv("GEMINI_AI_HEALTH_MODEL", "gemini-2.5-flash")

    async def explain_dashboard(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        system = (
            "You are LightSignal Dashboard Explainer. "
            "Respond ONLY with JSON using four arrays: snapshot, positives, negatives, actions. "
            "Each array must contain short bullet strings (max 20 words). "
            "Tone is calm, plain English."
        )
        instruction = {
            "snapshot": "Key headline bullets describing current KPIs.",
            "positives": "What's going well and why.",
            "negatives": "What's concerning or off-track.",
            "actions": "2-4 next steps tied to metrics.",
        }
        body = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": json.dumps(
                                {
                                    "instructions": instruction,
                                    "inputs": payload,
                                },
                                default=str,
                            )
                        }
                    ],
                }
            ],
        }
        target_model = self.dashboard_model
        return await self._invoke_gemini(
            model=target_model,
            body=body,
        )

    async def explain_ai_health(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        system = (
            "You are LightSignal AI Health Explainer. "
            "Respond ONLY with JSON keys: meaning, shortfalls, improvements. "
            "Each key maps to an array of bullet strings. "
            "Write in simple, friendly language."
        )
        body = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": json.dumps(
                                {
                                    "score": payload.get("score"),
                                    "components": payload.get("components"),
                                },
                                default=str,
                            )
                        }
                    ],
                }
            ],
        }
        target_model = self.ai_health_model
        return await self._invoke_gemini(
            model=target_model,
            body=body,
        )

    async def _invoke_gemini(
        self,
        *,
        model: str,
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/{model}:generateContent"
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, params={"key": self.api_key}, json=body)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                # Surface a clear error when model/endpoint is invalid.
                detail = (
                    f"Gemini request failed ({response.status_code}): {response.text}. "
                    f"Check model '{model}' and base_url '{self.base_url}'."
                )
                raise httpx.HTTPStatusError(detail, request=exc.request, response=exc.response)

            payload = response.json()
            text = self._extract_text(payload)
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                parsed = self._maybe_parse_jsonish(text)
                if parsed is not None:
                    return parsed
                return {"text": text}

    def _maybe_parse_jsonish(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Try to parse JSON that may be wrapped in markdown code fences.
        """
        candidate = text.strip()
        if candidate.startswith("```"):
            lines = candidate.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            candidate = "\n".join(lines).strip()
        try:
            return json.loads(candidate)
        except Exception:
            return None

    def _extract_text(self, payload: Dict[str, Any]) -> str:
        candidates = payload.get("candidates") or []
        for candidate in candidates:
            content = candidate.get("content", {})
            parts = content.get("parts") or []
            if parts:
                text = parts[0].get("text")
                if text:
                    return text
        raise ValueError("No content returned from Gemini")

