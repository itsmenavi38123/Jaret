from app.utils.prompt_loader import load_canonical_prompt

DEMAND_FORECAST_PROMPT_FILENAME = "LightSignal_Demand_Forecast_Analyst_Prompt_v2.txt"


def get_demand_forecast_prompt() -> str:
    """
    Returns the verbatim Canonical LightSignal Demand Forecast Analyst Prompt v2.
    """
    return load_canonical_prompt(DEMAND_FORECAST_PROMPT_FILENAME)
