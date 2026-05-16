from pathlib import Path
from typing import Iterator

from core.llm import complete_json, complete_stream
from core.models import CriticReview, DebateState
from core.modes import ReviewMode, apply_addendum
from core.text import number_lines
from core.transcript import build_debate_user_prompt

PROMPT_PATH = Path(__file__).parent / "prompts" / "critic_system.md"


def _load_prompt(mode: ReviewMode = ReviewMode.STANDARD) -> str:
    base = PROMPT_PATH.read_text(encoding="utf-8")
    return apply_addendum(base, mode, "CRITIC")


def review(
    code: str,
    language: str | None = None,
    mode: ReviewMode = ReviewMode.STANDARD,
) -> CriticReview:
    """Initial structured review. Returns a parsed CriticReview."""
    system_prompt = _load_prompt(mode)
    lang_hint = f" ({language})" if language else ""
    user_prompt = (
        f"## Mode: INITIAL REVIEW (structured JSON output)\n\n"
        f"Review the following code{lang_hint}. Line numbers are shown to the left of each line.\n\n"
        f"```\n{number_lines(code)}\n```\n\n"
        f"Respond with valid JSON only, matching the schema in your system instructions."
    )
    raw = complete_json(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.6)
    return CriticReview.model_validate_json(raw)


def rebut_stream(state: DebateState, round_number: int) -> Iterator[str]:
    """Streamed prose response from the Critic during a debate turn (round >= 2)."""
    system_prompt = _load_prompt(state.mode)
    user_prompt = build_debate_user_prompt(state, role="CRITIC", round_number=round_number)
    yield from complete_stream(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.7)
