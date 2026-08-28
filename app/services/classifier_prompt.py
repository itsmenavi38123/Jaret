from app.utils.prompt_loader import load_canonical_prompt

CLASSIFIER_PROMPT_FILENAME = "LightSignal_Classifier_Prompt_V4_1.txt"


def get_classifier_prompt() -> str:
    """
    Returns the verbatim Canonical LightSignal Classifier Prompt V4.1.
    Performs full 10-dimension business classification, tier B signals, peer pool mapping,
    geographic anchor derivation, and tensions detection.
    """
    return load_canonical_prompt(CLASSIFIER_PROMPT_FILENAME)
