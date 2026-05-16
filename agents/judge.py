from pathlib import Path

from core.llm import complete_json
from core.models import DebateState, Verdict
from core.modes import apply_addendum
from core.transcript import build_judge_user_prompt

PROMPT_PATH = Path(__file__).parent / "prompts" / "judge_system.md"


def _load_prompt(state: DebateState) -> str:
    base = PROMPT_PATH.read_text(encoding="utf-8")
    return apply_addendum(base, state.mode, "JUDGE")


def synthesize(state: DebateState) -> Verdict:
    """Read the full debate and produce a structured verdict. One-shot, low temperature."""
    system_prompt = _load_prompt(state)
    user_prompt = build_judge_user_prompt(state)
    raw = complete_json(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.3)
    return Verdict.model_validate_json(raw)
