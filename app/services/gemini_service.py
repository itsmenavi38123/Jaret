"""
Gemini Service
Thin wrapper around Gemini 3 APIs with JSON-structured prompts plus fallbacks.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import httpx


class GeminiService:
    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.base_url = os.getenv(
            "GEMINI_API_BASE_URL",
            "https://generativelanguage.googleapis.com/v1beta/models",
        )
        self.dashboard_model = os.getenv("GEMINI_DASHBOARD_MODEL", "gemini-3.0-pro")
        self.ai_health_model = os.getenv("GEMINI_AI_HEALTH_MODEL", "gemini-3.0-pro")

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
            fallback=self._dashboard_fallback(payload),
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
            fallback=self._ai_health_fallback(payload),
        )

    async def _invoke_gemini(
        self,
        *,
        model: str,
        body: Dict[str, Any],
        fallback: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not self.api_key:
            return fallback

        url = f"{self.base_url}/{model}:generateContent"
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(url, params={"key": self.api_key}, json=body)
                response.raise_for_status()
                payload = response.json()
                text = self._extract_text(payload)
                return json.loads(text)
        except Exception as exc:
            print(f"Gemini call failed: {exc}")
            return fallback

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

    def _dashboard_fallback(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        kpis = payload.get("kpis", {})
        alerts = payload.get("alerts", [])

        def summarize_kpi(key: str, label: str) -> str:
            value = kpis.get(key, {}).get("value")
            if value is None:
                return f"{label}: pending sync."
            if "margin" in key:
                return f"{label}: {value * 100:.1f}%."
            return f"{label}: ${value:,.0f}."

        snapshot = [
            summarize_kpi("revenue_mtd", "Revenue MTD"),
            summarize_kpi("cash", "Cash"),
            summarize_kpi("runway_months", "Runway"),
        ]
        positives = ["No critical system issues detected."]
        negatives = [alert.get("title") for alert in alerts[:2]] or ["Awaiting more data."]
        actions = ["Keep accounts synced", "Review latest alerts"]

        return {
            "snapshot": snapshot,
            "positives": positives,
            "negatives": negatives,
            "actions": actions,
        }

    def _ai_health_fallback(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        score = payload.get("score", 60)
        components = payload.get("components", [])

        meaning = [
            f"AI Health Score is {score} / 100.",
            "Higher scores mean more complete, reliable data for AI features.",
        ]
        shortfalls = []
        improvements = []

        for component in components:
            label = component.get("label", "Component")
            comp_score = component.get("score", 0)
            note = component.get("note", "")
            if comp_score < 70:
                shortfalls.append(f"{label} is {comp_score}/100. {note}")
                improvements.append(f"Boost {label.lower()} to raise the score.")

        if not shortfalls:
            shortfalls = ["No major gaps detected."]
        if not improvements:
            improvements = ["Keep connecting data sources to maintain score."]

        return {
            "meaning": meaning,
            "shortfalls": shortfalls,
            "improvements": improvements,
        }

