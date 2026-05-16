from pathlib import Path
from typing import Iterator

from core.llm import complete_stream
from core.models import DebateState
from core.transcript import build_debate_user_prompt

PROMPT_PATH = Path(__file__).parent / "prompts" / "advocate_system.md"


def _load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def rebut_stream(state: DebateState, round_number: int) -> Iterator[str]:
    """Streamed prose response from the Advocate during a debate turn."""
    system_prompt = _load_prompt()
    user_prompt = build_debate_user_prompt(state, role="ADVOCATE", round_number=round_number)
    yield from complete_stream(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.75)
