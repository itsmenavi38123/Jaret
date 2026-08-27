from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from app.services.claude_service import claude_service
import json


def _stringify_ids(obj: Any) -> Any:
    if hasattr(obj, "__str__") and type(obj).__name__ == "ObjectId":
        return str(obj)
    elif isinstance(obj, dict):
        return {str(k): _stringify_ids(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return [_stringify_ids(x) for x in obj]
    return obj


from pathlib import Path

def _load_canonical_prompt(filename: str) -> str:
    try:
        base_dir = Path(__file__).resolve().parent.parent.parent
        prompt_path = base_dir / "CANONICAL — FINAL SPECS ONLY" / "10_Agent_Prompts_CANON" / filename
        if prompt_path.exists():
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
    except Exception as e:
        print(f"Error loading canonical prompt {filename}: {e}")
    return ""


class PrepAgentService:

    def __init__(self):
        pass

    async def generate_preparation_guidance(
        self,
        opportunity: Dict[str, Any],
        business_profile: Dict[str, Any],
        classifier_output: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        system_prompt = _load_canonical_prompt("Opportunity_Prep_Agent_System_Prompt_v2_DF.txt")
        if not system_prompt:
            system_prompt = """You are the Opportunity Preparation Agent for LightSignal.
Your job is to generate preparation guidance for a business opportunity (events, festivals, vendor spots, contracts, grants).
Return STRICT JSON only containing checklist, judgment_prompts, and checkpoint_summary."""

        clean_opportunity = _stringify_ids(opportunity or {})
        clean_profile = _stringify_ids(business_profile or {})
        clean_classifier = _stringify_ids(classifier_output or {})

        last_error = None
        for _ in range(2):
            try:
                parsed = await claude_service.json_completion(
                    system_prompt=system_prompt,
                    user_content={
                        "opportunity": clean_opportunity,
                        "business_profile": clean_profile,
                        "classifier_output": clean_classifier,
                    },
                    temperature=0.2,
                    max_tokens=3000,
                )

                if isinstance(parsed, dict):
                    return self.validate_prep_output(parsed, clean_opportunity)
            except Exception as e:
                last_error = e

        # Fallback to deterministic structure if live Claude call completely fails
        return self._build_deterministic_prep(clean_opportunity)

    def validate_prep_output(
        self,
        output: Dict[str, Any],
        opportunity: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        opportunity = opportunity or {}
        now = datetime.utcnow()

        raw_checklist = output.get("checklist") or []
        raw_prompts = output.get("judgment_prompts") or output.get("risk_prompts") or []

        cleaned_checklist: List[Dict[str, Any]] = []
        for i, item in enumerate(raw_checklist):
            if not isinstance(item, dict):
                continue
            
            task_label = item.get("label") or item.get("title") or item.get("task") or "Preparation task"
            phase = item.get("phase") or "7_10_days"
            priority = str(item.get("priority", "standard")).lower()
            if priority not in ["critical", "standard", "nice_to_have", "high", "medium", "low"]:
                priority = "standard"
            
            is_urgent = bool(item.get("is_urgent", priority in ["critical", "high"]))
            addresses = item.get("addresses") or "operational"
            deadline = item.get("deadline_date") or (now + timedelta(days=(i + 1) * 4)).strftime("%Y-%m-%d")

            cleaned_checklist.append({
                "task_id": item.get("task_id") or item.get("task_key") or f"chk_{i+1}",
                "label": task_label,
                "title": task_label,
                "phase": phase,
                "deadline_date": deadline,
                "priority": priority,
                "is_urgent": is_urgent,
                "addresses": addresses,
                "completed": bool(item.get("completed", False))
            })

        cleaned_prompts: List[Dict[str, Any]] = []
        for item in raw_prompts:
            if not isinstance(item, dict):
                continue
            
            category = item.get("category") or item.get("panel_name") or "Operational Drag"
            check_prompt = item.get("check_prompt") or item.get("prompt") or item.get("title") or item.get("description") or ""
            severity = str(item.get("severity", "medium")).lower()
            if severity not in ["high", "medium", "low"]:
                severity = "medium"

            if check_prompt:
                cleaned_prompts.append({
                    "category": category,
                    "check_prompt": check_prompt,
                    "prompt": check_prompt,
                    "title": category,
                    "description": check_prompt,
                    "severity": severity
                })

        summary = output.get("checkpoint_summary")
        if isinstance(summary, dict):
            summary_text = summary.get("text") or "Preparation tracking active. Complete checklist items to stay on schedule."
        elif isinstance(summary, str):
            summary_text = summary
        else:
            summary_text = f"Preparation plan active for {opportunity.get('title', 'opportunity')}. Review checkpoints prior to commitment."

        return {
            "opportunity_id": opportunity.get("id") or str(opportunity.get("_id", "")),
            "checklist": cleaned_checklist if len(cleaned_checklist) >= 2 else self._build_default_checklist(now),
            "judgment_prompts": cleaned_prompts if len(cleaned_prompts) >= 2 else self._build_default_prompts(),
            "risk_prompts": cleaned_prompts if len(cleaned_prompts) >= 2 else self._build_default_prompts(),
            "checkpoint_summary": summary_text,
            "cash_balance": opportunity.get("cash_balance", 0.0),
            "revenue_attributed": opportunity.get("revenue_attributed", 0.0),
            "owner_responses": opportunity.get("owner_responses", {})
        }

    def _build_default_checklist(self, now: datetime) -> List[Dict[str, Any]]:
        return [
            {
                "task_id": "chk_1",
                "label": "Confirm staffing schedule and shift coverage",
                "title": "Confirm staffing schedule and shift coverage",
                "phase": "2_3_weeks_before",
                "deadline_date": (now + timedelta(days=7)).strftime("%Y-%m-%d"),
                "priority": "critical",
                "is_urgent": True,
                "addresses": "operational",
                "completed": False
            },
            {
                "task_id": "chk_2",
                "label": "Review inventory stock levels and supplier lead times",
                "title": "Review inventory stock levels and supplier lead times",
                "phase": "7_10_days",
                "deadline_date": (now + timedelta(days=12)).strftime("%Y-%m-%d"),
                "priority": "standard",
                "is_urgent": False,
                "addresses": "financial",
                "completed": False
            },
            {
                "task_id": "chk_3",
                "label": "Verify POS terminal connectivity and payment processing",
                "title": "Verify POS terminal connectivity and payment processing",
                "phase": "event_week",
                "deadline_date": (now + timedelta(days=18)).strftime("%Y-%m-%d"),
                "priority": "standard",
                "is_urgent": False,
                "addresses": "operational",
                "completed": False
            }
        ]

    def _build_default_prompts(self) -> List[Dict[str, Any]]:
        return [
            {
                "category": "Human Factors",
                "check_prompt": "Will key team members require overtime or temporary shift reassignment to support this?",
                "prompt": "Will key team members require overtime or temporary shift reassignment to support this?",
                "title": "Human Factors",
                "description": "Staffing and schedule trade-offs during commitment window.",
                "severity": "medium"
            },
            {
                "category": "Financial Ripple",
                "check_prompt": "What is the expected ROI multiple relative to upfront inventory and deposit costs?",
                "prompt": "What is the expected ROI multiple relative to upfront inventory and deposit costs?",
                "title": "Financial Ripple",
                "description": "Cash flow timing and vendor payment commitments.",
                "severity": "low"
            }
        ]

    def _build_deterministic_prep(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.utcnow()
        title = opportunity.get("title", "this opportunity")
        return {
            "opportunity_id": opportunity.get("id") or str(opportunity.get("_id", "")),
            "checklist": self._build_default_checklist(now),
            "judgment_prompts": self._build_default_prompts(),
            "risk_prompts": self._build_default_prompts(),
            "checkpoint_summary": f"Preparation tracking active for {title}. Complete checklist items to maintain operational momentum.",
            "cash_balance": opportunity.get("cash_balance", 0.0),
            "revenue_attributed": opportunity.get("revenue_attributed", 0.0),
            "owner_responses": opportunity.get("owner_responses", {})
        }


prep_agent_service = PrepAgentService()