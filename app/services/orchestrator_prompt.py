from app.utils.prompt_loader import load_canonical_prompt

ORCHESTRATOR_PROMPT_FILENAME = "Orchestrator_v3_7_System_Prompt_DF.txt"


def get_orchestrator_prompt() -> str:
    """
    Returns the verbatim Canonical Orchestrator v3.7 System Prompt.
    Covers: ASK MODE, HEALTH NARRATIVE MODE, WATCH AREA INVESTIGATION, OPPORTUNITY SYNTHESIS, etc.
    """
    return load_canonical_prompt(ORCHESTRATOR_PROMPT_FILENAME)
