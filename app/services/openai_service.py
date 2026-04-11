import os
import json
import re
from typing import Dict, Any
from openai import AsyncOpenAI


client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class OpenAIService:

    async def explain_kpi_drawer(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calls OpenAI using client agent prompt (DRAWER MODE)
        and returns structured KPI explanation JSON.
        """

        prompt = self._build_prompt(payload)

        try:
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are the LightSignal Financial Analyst. Follow instructions strictly."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content

            return self._safe_parse_json(content)

        except Exception as exc:
            raise Exception(f"OpenAI KPI explanation failed: {exc}")

    def _build_prompt(self, payload: Dict[str, Any]) -> str:
        return f"""
You are the LightSignal Financial Analyst.

Explain {payload.get("kpi_name")}. Output ONLY valid JSON.

Context:
- KPI Name: {payload.get("kpi_name")}
- Current Value: {payload.get("current_value")}
- Prior Value: {payload.get("prior_value")}
- Format Type: {payload.get("format_type")}

Optional Context:
{json.dumps(payload.get("optional_context", {}), indent=2)}
Benchmark data (if present) is located at optional_context.benchmarks.
Use this data for vs_peers calculations.

STRICT RULES:
- Follow DRAWER MODE exactly
- Return ONLY JSON (no explanation text)
- Do NOT hallucinate missing values
- Use ONLY data provided
- Respect all character limits

REQUIREMENTS:
- verdict (max 200 chars)
- status (healthy/watch/critical)
- comparison (vs_last_period REQUIRED)
- 2-3 drivers (ranked by impact)
- 2-3 actions (specific and practical)

STATUS RULES:
- revenue: >5% healthy, ±5% watch, < -5% critical
- net_margin: >10% healthy, 0–10% watch, <0% critical
- runway: >6 healthy, 3–6 watch, <3 critical
- score: >70 healthy, 50–70 watch, <50 critical

VS_PEERS RULES:
- Benchmark data is available at optional_context.benchmarks

- If optional_context.benchmarks contains data for this KPI:
  - Extract the metric object (e.g. {{"median": ..., "p25": ..., "p75": ..., "source": ...}})
  - Use ONLY the "median" value as benchmark_value
  - Do NOT use p25 or p75

  - Compare current_value with benchmark_value:
      above → current_value > benchmark_value
      below → current_value < benchmark_value
      at_par → within 5 percent range

  - Generate gap_text like:
    "X percent above industry median"
    "X percent below industry median"

  - Use "source" as benchmark_source if available

- If benchmark median is null or benchmark data is missing:
  - Set all vs_peers fields to null

DATA CONFIDENCE RULES:
- Score based on:
  - data completeness
  - availability of prior value
  - availability of context
- If only current + prior → Moderate (~60)
- If missing prior → Low (~30)
- If rich context available → High (~80+)

OUTPUT FORMAT:
{{
  "verdict": "string",
  "status": "healthy" | "watch" | "critical",
  "comparison": {{
    "vs_last_period": {{
      "change_text": "string",
      "direction": "up" | "down" | "flat"
    }},
    "vs_peers": {{
      "benchmark_value": number or null,
      "benchmark_source": string or null,
      "position": "above" | "below" | "at_par" | null,
      "gap_text": "string" or null
    }},
    "vs_target": {{
      "target_value": null,
      "gap_text": null,
      "on_track": null
    }}
  }},
  "drivers": [
    {{
      "description": "string",
      "impact": "string",
      "category": "string"
    }}
  ],
  "actions": [
    {{
      "description": "string",
      "priority": "high" | "medium" | "low",
      "effort": "quick_win" | "moderate" | "long_term"
    }}
  ],
  "data_confidence": {{
    "score": 0,
    "label": "High" | "Moderate" | "Low",
    "factors": [
      "string",
      "string"
    ]
  }}
}}
"""
    def _safe_parse_json(self, content: str) -> Dict[str, Any]:
        """
        Ensures OpenAI response is valid JSON.
        Handles cases like:
        - json\n{...}
        - ```json {...} ```
        """

        try:
            return json.loads(content)

        except json.JSONDecodeError:
            try:
                content = content.strip()
                content = re.sub(r"^```json", "", content)
                content = re.sub(r"^```", "", content)
                content = re.sub(r"^json", "", content)
                content = content.replace("```", "")
                content = content.strip()
                return json.loads(content)

            except Exception:
                raise ValueError(f"Invalid JSON from OpenAI: {content}")
            



    async def ask_kpi_ai(self, payload: Dict[str, Any]) -> Dict[str, Any]:


        messages = self._build_chat_messages(payload)

        try:
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.4,
            )

            content = response.choices[0].message.content.strip()

            return {
                "answer": content
            }

        except Exception as exc:
            raise Exception(f"KPI chat failed: {exc}")


    def _build_chat_messages(self, payload: Dict[str, Any]):
        system_prompt = """
You are the LightSignal Financial Analyst.

Answer in 2–4 short paragraphs.
Do not use bullet points or numbering.
Be conversational and natural.
"""

        messages = [
            {"role": "system", "content": system_prompt}
        ]

        history = payload.get("chat_history", [])[-5:]
        messages.extend(history)

        user_prompt = f"""
User is viewing KPI: {payload.get("kpi_name")}

Context:
- Current Value: {payload.get("current_value")}
- Prior Value: {payload.get("prior_value")}

Additional Context:
{json.dumps(payload.get("optional_context", {}), indent=2)}

User Question:
{payload.get("question")}
"""

        messages.append({
            "role": "user",
            "content": user_prompt
        })

        return messages