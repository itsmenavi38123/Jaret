from app.utils.prompt_loader import load_canonical_prompt

SCENARIO_LAB_PROMPT_FILENAME = "LightSignal_Scenario_Lab_System_Prompt_v1_4.txt"


def get_scenario_lab_prompt() -> str:
    """
    Returns the verbatim Canonical Scenario Lab System Prompt v1.4.
    """
    return load_canonical_prompt(SCENARIO_LAB_PROMPT_FILENAME)
