import re
from enum import Enum
from pathlib import Path


class ReviewMode(str, Enum):
    ROAST = "roast"
    STANDARD = "standard"
    DEEP = "deep"


MAX_ROUNDS: dict[ReviewMode, int] = {
    ReviewMode.ROAST: 2,
    ReviewMode.STANDARD: 3,
    ReviewMode.DEEP: 5,
}


_MODES_DIR = Path(__file__).parent.parent / "agents" / "prompts" / "modes"


def _parse_sections(text: str) -> dict[str, str]:
    """Parse a mode markdown file into {AGENT_NAME: body} chunks.

    Section delimiter is a level-2 header like `## CRITIC`. Any preamble before
    the first header is ignored.
    """
    sections: dict[str, str] = {}
    current_name: str | None = None
    current_body: list[str] = []
    for line in text.splitlines():
        header_match = re.match(r"^##\s+([A-Z]+)\s*$", line.strip())
        if header_match:
            if current_name is not None:
                sections[current_name] = "\n".join(current_body).strip()
            current_name = header_match.group(1)
            current_body = []
        elif current_name is not None:
            current_body.append(line)
    if current_name is not None:
        sections[current_name] = "\n".join(current_body).strip()
    return sections


def load_addendum(mode: ReviewMode, agent: str) -> str:
    """Return the prompt overlay for (mode, agent), or empty string if none.

    `agent` is one of CRITIC, ADVOCATE, JUDGE.
    """
    if mode == ReviewMode.STANDARD:
        return ""
    path = _MODES_DIR / f"{mode.value}.md"
    if not path.exists():
        return ""
    sections = _parse_sections(path.read_text(encoding="utf-8"))
    return sections.get(agent.upper(), "")


def apply_addendum(base_prompt: str, mode: ReviewMode, agent: str) -> str:
    """Append the mode overlay to the base system prompt if there is one."""
    overlay = load_addendum(mode, agent)
    if not overlay:
        return base_prompt
    return (
        f"{base_prompt}\n\n"
        f"---\n\n"
        f"## MODE OVERLAY: {mode.value.upper()}\n\n"
        f"The following overrides apply to this turn. Where this overlay conflicts "
        f"with your base instructions, the overlay wins.\n\n"
        f"{overlay}"
    )
