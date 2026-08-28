from app.utils.prompt_loader import load_canonical_prompt

FINANCIAL_ANALYST_PROMPT_FILENAME = "Financial_Analyst_Prompt_V6.txt"


def get_financial_analyst_prompt() -> str:
    """
    Returns the verbatim Canonical Financial Analyst Prompt V6.
    Covers: DRAWER MODE, INSIGHTS MODE, DASHBOARD MODE, SCENARIO MODE, OPPORTUNITY WHY SUGGESTED MODE, CHAT MODE.
    """
    return load_canonical_prompt(FINANCIAL_ANALYST_PROMPT_FILENAME)


# For backward compatibility
FINANCIAL_OVERVIEW_DRAWER_PROMPT = get_financial_analyst_prompt()