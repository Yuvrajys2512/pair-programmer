from pathlib import Path

from core.llm import complete_json
from core.models import FixerResult, Verdict
from core.transcript import build_fixer_user_prompt

PROMPT_PATH = Path(__file__).parent / "prompts" / "fixer_system.md"


def fix(code: str, verdict: Verdict, language: str | None = None) -> FixerResult:
    """Rewrite code to address exactly the verdict's action items. One-shot, low temperature."""
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    user_prompt = build_fixer_user_prompt(code, verdict, language)
    raw = complete_json(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.2)
    return FixerResult.model_validate_json(raw)
