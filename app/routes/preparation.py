from fastapi import APIRouter, FastAPI
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime, date
import copy
import os

router = APIRouter(tags=["Opportunities"])

app = FastAPI(title="Opportunity Preparation API")
app.include_router(router)


USE_OPENAI = bool(os.getenv("OPENAI_API_KEY"))
if USE_OPENAI:
    from openai import OpenAI
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class OpportunityInput(BaseModel):
    title: str
    type: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    location: str
    listed_fee: Optional[float] = None
    potential_value: Optional[float] = None
    fit_score: Optional[float] = None
    readiness_score: Optional[float] = None
    expected_roi: Optional[float] = None
    suggestion: List[str] = []
    source_url: str

    permits_required: Optional[bool] = None
    weather_score: Optional[int] = None
    financial_score: Optional[int] = None
    peer_benchmark: Optional[bool] = None

    business_type: Optional[str] = "generic business"
    use_ai: bool = True


GENERIC_CAPABILITY_PLAYBOOK = {
    "2–3 Weeks Before": [
        "inventory_planning",
        "pricing_strategy",
        "staffing_plan",
        "marketing_prep"
    ],
    "7–10 Days Before": [
        "inventory_finalization",
        "staff_scheduling",
        "logistics_check",
        "payment_setup"
    ],
    "Event Week / Execution": [
        "on_site_setup",
        "customer_flow_management",
        "sales_execution"
    ],
    "Risks & Gotchas": [
        "inventory_shortage",
        "staffing_gap",
        "high_footfall"
    ]
}

ESSENTIAL_CAPABILITIES = {
    "inventory_planning",
    "pricing_strategy",
    "staffing_plan",
    "on_site_setup",
    "sales_execution"
}


def fallback_text(capabilities: List[str]) -> List[str]:
    return [c.replace("_", " ").capitalize() for c in capabilities]


def generate_tasks_with_ai(
    capabilities: List[str],
    opportunity: OpportunityInput,
    section: str
) -> List[str]:

    if not USE_OPENAI or not opportunity.use_ai:
        return fallback_text(capabilities)

    prompt = f"""
Business type: {opportunity.business_type}
Opportunity: {opportunity.title}
Location: {opportunity.location}
Timeline phase: {section}

Convert the following preparation areas into simple, clear, actionable tasks.

Rules:
- Do NOT use headings, markdown, bold text, or numbering
- Each line must be a single actionable task
- Start each task with a verb
- Keep each task under 20 words
- Do NOT repeat section names
- Return only bullet points

Preparation areas:
{', '.join(capabilities)}
"""

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return [
        line.strip("- ").strip()
        for line in response.choices[0].message.content.split("\n")
        if line.strip()
    ]

def build_preparation(opportunity: OpportunityInput):
    base = copy.deepcopy(GENERIC_CAPABILITY_PLAYBOOK)
    sections: Dict[str, List[str]] = {}

    days_to_start = None
    if opportunity.start_date:
        start_date = datetime.strptime(opportunity.start_date, "%Y-%m-%d").date()
        days_to_start = (start_date - date.today()).days

    if days_to_start is None or days_to_start >= 14:
        preparedness = "On Track"
        urgency = False
        sections = base

    elif 7 <= days_to_start < 14:
        preparedness = "At Risk"
        urgency = True

        merged = [
            c for c in base["2–3 Weeks Before"]
            if c in ESSENTIAL_CAPABILITIES
        ] + base["7–10 Days Before"]

        sections = {
            "Immediate Focus (Next 7–10 Days)": merged,
            "Event Week / Execution": base["Event Week / Execution"],
            "Risks & Gotchas": base["Risks & Gotchas"] + ["compressed_timeline"]
        }

    else:
        preparedness = "At Risk"
        urgency = True

        immediate = []
        for sec in ["2–3 Weeks Before", "7–10 Days Before"]:
            for c in base[sec]:
                if c in ESSENTIAL_CAPABILITIES:
                    immediate.append(c)

        sections = {
            "Immediate Actions (Next 48–72 hrs)": immediate,
            "Event Week / Execution": [
                c for c in base["Event Week / Execution"]
                if c in ESSENTIAL_CAPABILITIES
            ],
            "Risks & Gotchas": base["Risks & Gotchas"] + ["very_limited_time"]
        }

    first_section = list(sections.keys())[0]

    if opportunity.permits_required:
        sections[first_section].append("regulatory_compliance")

    if opportunity.weather_score is not None and opportunity.weather_score < 70:
        sections["Risks & Gotchas"].append("weather_disruption")

    if opportunity.financial_score is not None and opportunity.financial_score < 60:
        sections[first_section].append("cash_flow_buffer")

    final_sections = {}
    for section, capabilities in sections.items():
        final_sections[section] = generate_tasks_with_ai(
            capabilities, opportunity, section
        )

    confidence_inputs = [
        opportunity.potential_value,
        opportunity.listed_fee,
        opportunity.weather_score,
        opportunity.peer_benchmark
    ]
    score = sum(1 for i in confidence_inputs if i is not None) / 4

    confidence = (
        "High" if score >= 0.75 else
        "Medium" if score >= 0.5 else
        "Low"
    )

    return final_sections, preparedness, confidence, days_to_start, urgency


@router.post("/preparation")
def generate_preparation(opportunity: OpportunityInput):
    sections, preparedness, confidence, days_to_start, urgency = build_preparation(opportunity)

    return {
        "opportunity_title": opportunity.title,
        "opportunity_type": opportunity.type,
        "days_to_start": days_to_start,
        "preparedness_status": preparedness,
        "urgency": urgency,
        "confidence": confidence,
        "sections": sections
    }
