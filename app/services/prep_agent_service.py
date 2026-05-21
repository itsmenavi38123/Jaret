from typing import Dict, Any
from openai import AsyncOpenAI
import os
import json


class PrepAgentService:

    def __init__(self):
        pass

    async def generate_preparation_guidance(
        self,
        opportunity: Dict[str, Any],
        business_profile: Dict[str, Any],
    ):

        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError("OPENAI_API_KEY not found")

        client = AsyncOpenAI(api_key=api_key)

        system_prompt = """
You are LightSignal Prep Agent.

Your job is to generate preparation guidance for a business opportunity.

Return STRICT JSON only.

Required output format:

{
  "checklist": [
    {
      "title": "",
      "description": "",
      "priority": "high|medium|low"
    }
  ],
  "risk_prompts": [
    {
      "title": "",
      "description": "",
      "severity": "high|medium|low"
    }
  ]
}

Rules:
- checklist must contain 5-10 items.
- risk_prompts must contain 3-6 items.
- Be specific to the opportunity and business profile.
- Do not use markdown.
- Do not return anything outside JSON.
"""

        last_error = None

        for _ in range(2):

            try:

                response = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt,
                        },
                        {
                            "role": "user",
                            "content": json.dumps({
                                "opportunity": opportunity,
                                "business_profile": business_profile,
                            }, default=str)
                        }
                    ],
                    response_format={"type": "json_object"}
                )

                content = response.choices[0].message.content

                parsed = json.loads(content)

                validated = self.validate_prep_output(parsed)

                return validated

            except Exception as e:

                last_error = e

        raise ValueError(
            f"Prep Agent generation failed: {str(last_error)}"
        )

    def validate_prep_output(
        self,
        output: Dict[str, Any],
    ):

        checklist = output.get("checklist", [])
        risk_prompts = output.get("risk_prompts", [])

        if not isinstance(checklist, list):
            checklist = []

        if not isinstance(risk_prompts, list):
            risk_prompts = []

        cleaned_checklist = []

        for item in checklist:

            if not isinstance(item, dict):
                continue

            priority = (
                item.get("priority", "medium")
                .lower()
                .strip()
            )

            if priority not in ["high", "medium", "low"]:
                priority = "medium"

            cleaned_checklist.append({
                "title": item.get("title", ""),
                "description": item.get("description", ""),
                "priority": priority,
            })

        cleaned_risks = []

        for item in risk_prompts:

            if not isinstance(item, dict):
                continue

            severity = (
                item.get("severity", "medium")
                .lower()
                .strip()
            )

            if severity not in ["high", "medium", "low"]:
                severity = "medium"

            cleaned_risks.append({
                "title": item.get("title", ""),
                "description": item.get("description", ""),
                "severity": severity,
            })

        if len(cleaned_checklist) < 5:
            raise ValueError("Checklist must contain minimum 5 items")

        if len(cleaned_risks) < 3:
            raise ValueError("Risk prompts must contain minimum 3 items")

        return {
            "checklist": cleaned_checklist[:10],
            "risk_prompts": cleaned_risks[:6],
        }


prep_agent_service = PrepAgentService()