import shutil
from pathlib import Path
from typing import Dict

_PROMPT_CACHE: Dict[str, str] = {}

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CANONICAL_DIR = BASE_DIR / "CANONICAL — FINAL SPECS ONLY" / "10_Agent_Prompts_CANON"
APP_PROMPTS_DIR = BASE_DIR / "app" / "prompts"


def ensure_prompts_synced():
    """
    Ensures app/prompts folder exists and contains all duplicated prompt files
    from the canonical folder without modifying the client's canonical files.
    """
    APP_PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    if CANONICAL_DIR.exists():
        for src_file in CANONICAL_DIR.glob("*.txt"):
            dst_file = APP_PROMPTS_DIR / src_file.name
            if not dst_file.exists() or dst_file.stat().st_mtime < src_file.stat().st_mtime:
                shutil.copy2(src_file, dst_file)


# Initialize folder and copy files on module load
try:
    ensure_prompts_synced()
except Exception as e:
    pass


def load_canonical_prompt(filename: str) -> str:
    """
    Loads a system prompt verbatim from app/prompts/<filename>.
    Uses in-memory caching to avoid redundant disk reads.
    """
    if filename in _PROMPT_CACHE:
        return _PROMPT_CACHE[filename]

    prompt_path = APP_PROMPTS_DIR / filename

    # Fallback to copy if single file was missing
    if not prompt_path.exists() and CANONICAL_DIR.exists():
        src_path = CANONICAL_DIR / filename
        if src_path.exists():
            APP_PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, prompt_path)

    if prompt_path.exists():
        with open(prompt_path, "r", encoding="utf-8") as f:
            content = f.read()
            _PROMPT_CACHE[filename] = content
            return content

    raise FileNotFoundError(f"Prompt file not found in app/prompts: {prompt_path}")
