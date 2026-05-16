from pathlib import Path

from core.llm import complete_json
from core.models import CriticReview

PROMPT_PATH = Path(__file__).parent / "prompts" / "critic_system.md"


def _load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _number_lines(code: str) -> str:
    """Prefix each line with its 1-indexed line number so the model can cite accurately."""
    lines = code.splitlines()
    width = len(str(len(lines))) if lines else 1
    return "\n".join(f"{str(i + 1).rjust(width)} | {line}" for i, line in enumerate(lines))


def review(code: str, language: str | None = None) -> CriticReview:
    """Send code to the Critic and return a parsed review."""
    system_prompt = _load_prompt()
    lang_hint = f" ({language})" if language else ""
    user_prompt = (
        f"Review the following code{lang_hint}. Line numbers are shown to the left of each line.\n\n"
        f"```\n{_number_lines(code)}\n```"
    )
    raw = complete_json(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.6)
    return CriticReview.model_validate_json(raw)
