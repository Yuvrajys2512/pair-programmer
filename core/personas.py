"""Persona registry — composable identity overlays on top of the base agent
prompts and the mode overlay.

A persona changes WHO the Critic and Advocate are (FAANG interviewer, mentor,
staff engineer, security auditor) without changing the tone the mode dictates.
A persona file lives at agents/prompts/personas/<slug>.md and follows the same
section format as the mode files (## CRITIC, ## ADVOCATE, optionally ## JUDGE).

The first line of the file should be the display name as a top-level heading,
e.g. `# FAANG Interviewer`. The text between that heading and the first
section header is treated as the persona description (shown in the UI and
--list-personas).
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


_PERSONAS_DIR = Path(__file__).parent.parent / "agents" / "prompts" / "personas"


@dataclass(frozen=True)
class Persona:
    slug: str
    name: str
    description: str


def _parse_sections(text: str) -> dict[str, str]:
    """Same level-2 section parser as core.modes. Kept duplicated to avoid
    pulling modes into the personas module — they are intentionally independent
    overlays."""
    sections: dict[str, str] = {}
    current_name: Optional[str] = None
    current_body: list[str] = []
    for line in text.splitlines():
        header = re.match(r"^##\s+([A-Z]+)\s*$", line.strip())
        if header:
            if current_name is not None:
                sections[current_name] = "\n".join(current_body).strip()
            current_name = header.group(1)
            current_body = []
        elif current_name is not None:
            current_body.append(line)
    if current_name is not None:
        sections[current_name] = "\n".join(current_body).strip()
    return sections


def _parse_metadata(text: str) -> tuple[str, str]:
    """Return (display_name, description) from the persona file preamble.

    The display name is the first level-1 heading. The description is the
    paragraph(s) between that heading and the first level-2 section.
    """
    lines = text.splitlines()
    name = ""
    desc_lines: list[str] = []
    seen_h1 = False
    for line in lines:
        stripped = line.strip()
        if not seen_h1:
            m = re.match(r"^#\s+(.+)$", stripped)
            if m:
                name = m.group(1).strip()
                seen_h1 = True
            continue
        if re.match(r"^##\s+[A-Z]+\s*$", stripped):
            break
        desc_lines.append(line)
    desc = "\n".join(desc_lines).strip()
    # Collapse repeated blank lines for one-line tooltips.
    desc = re.sub(r"\n{2,}", " ", desc).replace("\n", " ")
    return name, desc


def list_personas() -> list[Persona]:
    """Return all personas discoverable on disk, sorted by slug."""
    if not _PERSONAS_DIR.exists():
        return []
    personas: list[Persona] = []
    for path in sorted(_PERSONAS_DIR.glob("*.md")):
        slug = path.stem
        text = path.read_text(encoding="utf-8")
        name, desc = _parse_metadata(text)
        personas.append(Persona(slug=slug, name=name or slug, description=desc))
    return personas


def _load_addendum(persona_slug: str, agent: str) -> str:
    """Return the persona section for the given agent, or '' if none."""
    if not persona_slug:
        return ""
    path = _PERSONAS_DIR / f"{persona_slug}.md"
    if not path.exists():
        return ""
    sections = _parse_sections(path.read_text(encoding="utf-8"))
    return sections.get(agent.upper(), "")


def apply_persona_addendum(base_prompt: str, persona_slug: Optional[str], agent: str) -> str:
    """Append the persona overlay to the (already mode-overlaid) base prompt.

    Personas are applied AFTER modes so the persona has the final say where
    the two overlays disagree.
    """
    if not persona_slug:
        return base_prompt
    overlay = _load_addendum(persona_slug, agent)
    if not overlay:
        return base_prompt
    persona_name = next(
        (p.name for p in list_personas() if p.slug == persona_slug),
        persona_slug,
    )
    return (
        f"{base_prompt}\n\n"
        f"---\n\n"
        f"## PERSONA OVERLAY: {persona_name}\n\n"
        f"The following overrides describe the identity you take on for this "
        f"review. Where this overlay conflicts with your mode overlay or base "
        f"instructions, this PERSONA overlay wins on matters of identity and "
        f"perspective. The mode overlay still controls tone and length.\n\n"
        f"{overlay}"
    )


def validate_persona(persona_slug: Optional[str]) -> Optional[str]:
    """Return the slug if valid (or None passes through). Raise ValueError otherwise."""
    if persona_slug is None or persona_slug == "":
        return None
    available = {p.slug for p in list_personas()}
    if persona_slug not in available:
        raise ValueError(
            f"Unknown persona '{persona_slug}'. "
            f"Available: {sorted(available) or '(none)'}"
        )
    return persona_slug
