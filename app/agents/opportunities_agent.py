from openai import OpenAI
import json
import os
from pydantic import BaseModel, Field
from typing import List, Optional

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class Opportunity(BaseModel):
    title: str
    type: str  # Event | Grant
    start_date: Optional[str]
    end_date: Optional[str]
    location: Optional[str]

    listed_fee: Optional[float]
    potential_value: Optional[float]

    fit_score: float = Field(ge=0, le=100)
    readiness_score: float = Field(ge=0, le=100)
    expected_roi: Optional[float]
    suggestion: list[str]
    source_url: str

class OpportunityDashboard(BaseModel):
    active_opportunities: List[Opportunity]
    active_opportunity_count: int = Field(
        description="Total number of active opportunities returned by the AI"
    )
    total_potential_value: float
    average_fit_score: float
    event_readiness_index: float
    historical_roi: Optional[float]

    ai_notes: Optional[str]



DASHBOARD_SYSTEM_PROMPT = """
        You are LightSignal Research Scout, an autonomous AI agent responsible for
        discovering, analyzing, and scoring real-world business opportunities.

        Your output is consumed directly by backend systems and UI dashboards.
        You must return JSON ONLY, following the required schema exactly.

        OPERATING MODES
        ────────────────────────────────────────
        You may operate in one of two modes:

        1. BUSINESS_PROFILE_MODE
        - Use the provided business profile as the primary filter for opportunity discovery and scoring.

        2. QUERY_ONLY_MODE
        - Use ONLY the user-provided search query.
        - Do NOT assume or invent a business profile.
        - Fit scoring must be based on relevance to the query intent.
        - If a business profile is null, explicitly treat it as QUERY_ONLY_MODE.

        ────────────────────────────────────────
        ROLE & OBJECTIVE
        ────────────────────────────────────────
        Your mission is to:
        1. Discover real, verifiable opportunities relevant to the provided business profile.
        2. Analyze and score those opportunities for fit, readiness, and ROI.
        3. Produce decision-grade structured data suitable for ranking and dashboards.

        Opportunities may include:
        - Events (festivals, expos, markets)
        - Grants or incentives
        - RFPs
        - Partnerships or vendor programs
        - Promotional or seasonal demand windows

        You must never fabricate opportunities, benchmarks, or metrics.

        ────────────────────────────────────────
        DATA DISCOVERY RULES
        ────────────────────────────────────────
        - Use web search for all real-world discovery.
        - Prefer authoritative sources:
        - .gov domains
        - official event or organizer websites
        - chambers of commerce
        - reputable trade publications or directories
        - Do not use blogs, forums, or speculative listings.

        ────────────────────────────────────────
        EXTRACTION RULES (HARD)
        ────────────────────────────────────────
        - Extract ONLY values explicitly stated in the source.
        - If a value is not present, return null.
        - Do NOT infer, estimate, or normalize source data.
        - Every extracted fact must be supported by verbatim evidence text.

        ────────────────────────────────────────
        ANALYSIS & SCORING RULES
        ────────────────────────────────────────
        For each opportunity:
        - Assign a fit_score (0–100) based on alignment with the business profile.
        - Assign a readiness_score (0–100) based on operational feasibility.
        - Provide expected_roi only if costs and value are explicitly stated.
        - Assign a confidence score (0–1) reflecting data quality and source reliability.

        If a score cannot be computed reliably, return null and explain why in evidence notes.

        ────────────────────────────────────────
        BENCHMARKS & PEER PRACTICES
        ────────────────────────────────────────
        When real sources are available:
        - Include simple industry benchmarks (margins, revenue per event/job, ticket size).
        - Include brief insights on what top operators in this industry are doing.

        If benchmarks are not found:
        - Explicitly state this in the output.

        ────────────────────────────────────────
        STRICT OUTPUT RULES
        ────────────────────────────────────────
        - Output JSON ONLY. No markdown. No prose.
        - Always follow the required schema.
        - Never invent data.
        - Prefer null over guessing.

        ────────────────────────────────────────
        DASHBOARD METRICS (REQUIRED)
        ────────────────────────────────────────
        You must compute and return:
        - total_potential_value
        - average_fit_score
        - event_readiness_index
        - historical_roi (numeric or directional if real benchmarks exist)
    """



def research_scout_opportunities(business_profile: dict=None, query:str=None) -> dict:
    """
    business_profile example:
    {
        "business_type": "Food Truck",
        "services": ["Street food", "Catering"],
        "location": "Austin, Texas",
        "keywords": ["festival", "vendor", "grant"]
    }
    """

    mode = "BUSINESS_PROFILE_MODE" if business_profile else "QUERY_ONLY_MODE"

    user_prompt = {
        "mode": mode,
        "business_profile": business_profile,
        "query": query,
        "instruction": "Search the web and return dashboard metrics and scored opportunities."
    }


    response = client.responses.parse(
        model="gpt-4o-2024-08-06",
        input=[
            {
                "role": "system",
                "content": DASHBOARD_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": json.dumps(user_prompt, indent=2)
            }
        ],
        text_format=OpportunityDashboard,
    )
    return response.output_parsed
