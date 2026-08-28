from app.utils.prompt_loader import load_canonical_prompt

RESEARCH_SCOUT_PROMPT_FILENAME = "Research_Scout_Prompt_V3_1_DF.txt"


def get_research_scout_prompt() -> str:
    """
    Returns the verbatim Canonical Research Scout Prompt V3.1.
    Covers: OPPORTUNITY DISCOVERY mode (all 14 opportunity types, 5-criteria gate,
    estimation policy, Type 1/Type 2 fields) and WATCH AREA INVESTIGATION mode.
    """
    return load_canonical_prompt(RESEARCH_SCOUT_PROMPT_FILENAME)
