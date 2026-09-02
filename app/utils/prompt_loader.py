import shutil
from pathlib import Path
from typing import Dict, List, Optional

_PROMPT_CACHE: Dict[str, str] = {}
_SKILL_CACHE: Dict[str, str] = {}

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CANONICAL_DIR = BASE_DIR / "CANONICAL — FINAL SPECS ONLY" / "10_Agent_Prompts_CANON"
CANONICAL_SKILLS_DIR = BASE_DIR / "CANONICAL — FINAL SPECS ONLY" / "11_Skills"

APP_PROMPTS_DIR = BASE_DIR / "app" / "prompts"
APP_SKILLS_DIR = BASE_DIR / "app" / "skills"

# The 4 cross-cutting canonical skills per Folder 11 / Prompt_Sync brief
CANONICAL_SKILL_FILENAMES: List[str] = [
    "anti_hallucination_rules.md",
    "multi_location_handling.md",
    "web_search_methodology.md",
    "signal_lever_scenario_opportunity_definitions.md",
]


def ensure_prompts_synced():
    """
    Ensures app/prompts and app/skills folders exist and contain all duplicated
    prompt and skill files from the canonical folders without modifying canonical source files.
    """
    APP_PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    if CANONICAL_DIR.exists():
        for src_file in CANONICAL_DIR.glob("*.txt"):
            dst_file = APP_PROMPTS_DIR / src_file.name
            if not dst_file.exists() or dst_file.stat().st_mtime < src_file.stat().st_mtime:
                shutil.copy2(src_file, dst_file)

    APP_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    if CANONICAL_SKILLS_DIR.exists():
        for src_file in CANONICAL_SKILLS_DIR.glob("*.md"):
            dst_file = APP_SKILLS_DIR / src_file.name
            if not dst_file.exists() or dst_file.stat().st_mtime < src_file.stat().st_mtime:
                shutil.copy2(src_file, dst_file)


# Initialize folders and copy files on module load
try:
    ensure_prompts_synced()
except Exception as e:
    pass


def load_canonical_skill(filename: str) -> str:
    """
    Loads a skill markdown file verbatim from app/skills/<filename>.
    Uses in-memory caching to avoid redundant disk reads.
    """
    if filename in _SKILL_CACHE:
        return _SKILL_CACHE[filename]

    skill_path = APP_SKILLS_DIR / filename

    # Fallback to copy if single file was missing
    if not skill_path.exists() and CANONICAL_SKILLS_DIR.exists():
        src_path = CANONICAL_SKILLS_DIR / filename
        if src_path.exists():
            APP_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, skill_path)

    if skill_path.exists():
        with open(skill_path, "r", encoding="utf-8") as f:
            content = f.read()
            _SKILL_CACHE[filename] = content
            return content

    raise FileNotFoundError(f"Skill file not found in app/skills: {skill_path}")


def get_skills_injection_text(skill_filenames: Optional[List[str]] = None) -> str:
    """
    Returns the concatenated text of the 4 canonical skills from Folder 11
    formatted for system prompt injection.
    """
    targets = skill_filenames or CANONICAL_SKILL_FILENAMES
    sections = []
    for fname in targets:
        try:
            content = load_canonical_skill(fname)
            sections.append(f"\n\n# =========================================================================\n# CANONICAL SKILL: {fname}\n# =========================================================================\n{content}")
        except Exception as e:
            print(f"[WARN] Failed to load canonical skill {fname}: {e}")

    return "\n".join(sections)


def load_canonical_prompt(filename: str, inject_skills: bool = True) -> str:
    """
    Loads a system prompt verbatim from app/prompts/<filename>.
    When inject_skills is True (default), appends the 4 canonical cross-cutting skills from Folder 11.
    Uses in-memory caching to avoid redundant disk reads.
    """
    cache_key = f"{filename}:injected={inject_skills}"
    if cache_key in _PROMPT_CACHE:
        return _PROMPT_CACHE[cache_key]

    prompt_path = APP_PROMPTS_DIR / filename

    # Fallback to copy if single file was missing
    if not prompt_path.exists() and CANONICAL_DIR.exists():
        src_path = CANONICAL_DIR / filename
        if src_path.exists():
            APP_PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, prompt_path)

    if prompt_path.exists():
        with open(prompt_path, "r", encoding="utf-8") as f:
            base_prompt = f.read()

        if inject_skills:
            skills_block = get_skills_injection_text()
            full_prompt = f"{base_prompt}\n\n# =========================================================================\n# CANONICAL SKILLS INJECTION (FOLDER 11)\n# ========================================================================={skills_block}"
        else:
            full_prompt = base_prompt

        _PROMPT_CACHE[cache_key] = full_prompt
        return full_prompt

    raise FileNotFoundError(f"Prompt file not found in app/prompts: {prompt_path}")
